# approval_handler.py

import json
from typing import List
from sqlalchemy.orm import Session
from schemas import QuoteDB, QuoteApprovalDB, QuoteGroupDB, QuoteToGroupDB, QuoteStatusEnum
from approval_prompts import get_formatted_approve_quote_prompt, get_formatted_group_quotes_prompt
from llm_handler import get_llm_response

# Define a batch size for grouping quotes to avoid exceeding LLM context window
# This value might need tuning based on average quote length and LLM capabilities.
# Assuming an average quote + metadata is ~200-500 tokens, 50 quotes might be a safe starting point for a 32k context window.
GROUPING_BATCH_SIZE = 20
# Define overlap for grouping batches to catch groups spanning across batch boundaries
GROUPING_OVERLAP_COUNT = 10 # Number of quotes to overlap between consecutive grouping batches

def approve_and_group_quotes(db: Session):
    """
    Main function to process all pending quotes for approval and grouping.
    The revised workflow prioritizes grouping, then approves/declines remaining ungrouped quotes.
    """
    print("Starting approval and grouping process...")

    # Step 0: Ensure all quotes in 'quotes' table have a corresponding 'QuoteApproval' entry
    print("Checking for quotes missing approval records and creating PENDING entries...")
    quotes_without_approval = db.query(QuoteDB).outerjoin(QuoteApprovalDB).filter(QuoteApprovalDB.id == None).all()
    if quotes_without_approval:
        print(f"Found {len(quotes_without_approval)} quotes missing approval records. Creating PENDING entries.")
        for quote in quotes_without_approval:
            approval_record = QuoteApprovalDB(
                quote_id=quote.id,
                status=QuoteStatusEnum.PENDING
            )
            db.add(approval_record)
        db.commit()
        print("Created PENDING approval records for missing quotes.")
    else:
        print("All quotes have approval records. No new PENDING entries created.")

    # Fetch all currently pending quotes for potential grouping
    # Order by ID to maintain some form of document order for the LLM
    all_pending_quotes = db.query(QuoteDB).join(QuoteApprovalDB).filter(QuoteApprovalDB.status == QuoteStatusEnum.PENDING).order_by(QuoteDB.id).all()
    print(f"Found {len(all_pending_quotes)} pending quotes to consider for grouping.")

    if not all_pending_quotes:
        print("No pending quotes to process. Exiting approval and grouping.")
        return

    # 1. Group all pending quotes first, in batches
    print("Starting grouping phase for all pending quotes (in batches)...")
    processed_quote_ids_in_groups = set()
    total_groups_created = 0

    # Process quotes in batches for grouping with overlap
    # The step size is batch_size - overlap_count to create overlapping windows
    step_size = GROUPING_BATCH_SIZE - GROUPING_OVERLAP_COUNT
    if step_size <= 0: # Ensure step_size is at least 1 to avoid infinite loops or invalid steps
        step_size = 1
        print("Warning: GROUPING_BATCH_SIZE is not greater than GROUPING_OVERLAP_COUNT. Setting step_size to 1.")

    num_batches = (len(all_pending_quotes) - GROUPING_OVERLAP_COUNT + step_size) // step_size if len(all_pending_quotes) > GROUPING_OVERLAP_COUNT else 1
    if len(all_pending_quotes) == 0: num_batches = 0 # Handle empty list case

    for i in range(0, len(all_pending_quotes), step_size):
        # Ensure the batch does not go out of bounds
        batch_end_index = min(i + GROUPING_BATCH_SIZE, len(all_pending_quotes))
        batch_quotes = all_pending_quotes[i:batch_end_index]

        # Skip if batch is too small to be meaningful for grouping (e.g., only overlap quotes)
        if len(batch_quotes) < 2: # A group needs at least 2 quotes
            continue

        batch_num = int(i / step_size) + 1
        print(f"Processing grouping batch {batch_num}/{num_batches} with {len(batch_quotes)} quotes (indices {i} to {batch_end_index-1}).")

        try:
            prompt = get_formatted_group_quotes_prompt(batch_quotes)
            response = get_llm_response(prompt, response_mime_type="application/json") # Expect JSON for grouping
            
            if response is None:
                print(f"Warning: LLM returned no response for grouping batch {batch_num}. Skipping this batch.")
                continue

            grouped_ids_lists_batch = json.loads(response)

            if not isinstance(grouped_ids_lists_batch, list):
                print(f"Warning: LLM returned non-list for grouping batch {batch_num}. Skipping grouping for this batch.")
                grouped_ids_lists_batch = [] # Ensure it's iterable

            for group_list in grouped_ids_lists_batch:
                if not isinstance(group_list, list) or len(group_list) < 2:
                    continue # Skip invalid or single-quote groups

                # Filter out quotes that have already been processed in a previous batch
                # This is crucial for overlapping windows to prevent duplicate groups or status changes
                group_list_filtered = [q_id for q_id in group_list if q_id not in processed_quote_ids_in_groups]
                
                if len(group_list_filtered) < 2: # After filtering, still need at least 2 quotes to form a group
                    continue

                # Create a new group
                new_group = QuoteGroupDB(name="LLM-Generated Group", description="Group created by LLM analysis.")
                db.add(new_group)
                db.flush() # To get the new_group.id

                print(f"Created new group {new_group.id} for quotes: {group_list_filtered}")
                total_groups_created += 1

                # Add quotes to the group and update their status to APPROVED
                for quote_id in group_list_filtered:
                    quote_to_group = db.query(QuoteDB).filter(QuoteDB.id == quote_id).first()
                    if quote_to_group and quote_to_group.approval.status == QuoteStatusEnum.PENDING:
                        existing_group_link = db.query(QuoteToGroupDB).filter_by(quote_id=quote_id).first()
                        if not existing_group_link:
                            db.add(QuoteToGroupDB(quote_id=quote_id, group_id=new_group.id))
                            quote_to_group.approval.status = QuoteStatusEnum.APPROVED
                            quote_to_group.approval.approved_by = "LLM_Grouped"
                            processed_quote_ids_in_groups.add(quote_id)
                        else:
                            print(f"Quote {quote_id} is already in group {existing_group_link.group_id}. Skipping.")
                    else:
                        print(f"Warning: LLM returned quote ID {quote_id} for grouping, but it was not pending or found. Skipping.")
            db.commit() # Commit after each batch's grouping
            print(f"Finished grouping batch {batch_num}. Quotes within groups are now APPROVED.")

        except json.JSONDecodeError:
            print(f"Error: LLM returned invalid JSON for grouping batch {batch_num}. Skipping grouping for this batch.")
            db.rollback()
        except Exception as e:
            print(f"An error occurred during grouping batch {batch_num}: {e}")
            db.rollback()

    print(f"Finished all grouping batches. Total groups created: {total_groups_created}.")

    # 2. Approve or Decline remaining ungrouped quotes
    print("Starting individual approval/decline phase for ungrouped quotes...")
    # Re-fetch pending quotes, excluding those just approved by grouping
    remaining_pending_quotes = db.query(QuoteDB).join(QuoteApprovalDB).filter(QuoteApprovalDB.status == QuoteStatusEnum.PENDING).all()
    print(f"Found {len(remaining_pending_quotes)} ungrouped pending quotes to process individually.")

    for quote in remaining_pending_quotes:
        try:
            # Ensure this quote was not processed by grouping in this run
            if quote.id in processed_quote_ids_in_groups:
                continue

            prompt = get_formatted_approve_quote_prompt(quote) # Use the modified approval prompt
            response = get_llm_response(prompt)
            decision = response.strip().upper()

            if decision in ["APPROVED", "DECLINED"]:
                quote.approval.status = QuoteStatusEnum[decision]
                quote.approval.approved_by = "LLM_Individual"
                print(f"Quote {quote.id} processed with status: {decision} (Individual)")
            else:
                print(f"Warning: LLM returned an invalid decision ('{decision}') for quote {quote.id}. Skipping individual approval.")

        except Exception as e:
            print(f"Error processing ungrouped quote {quote.id} for individual approval: {e}")
            db.rollback() # Rollback changes for this quote if an error occurs

    db.commit() # Commit all individual approvals after the loop
    print("Finished individual approval/decline phase for ungrouped quotes.")
    print("Approval and grouping process complete.")
