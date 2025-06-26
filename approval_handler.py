# approval_handler.py

import json
from typing import List
from sqlalchemy.orm import Session
from schemas import QuoteDB, QuoteApprovalDB, QuoteGroupDB, QuoteToGroupDB, QuoteStatusEnum
from approval_prompts import get_formatted_approve_quote_prompt, get_formatted_group_quotes_prompt
from llm_handler import get_llm_response  # Assuming a generic LLM call function

def approve_and_group_quotes(db: Session):
    """
    Main function to process all pending quotes for approval and grouping.
    The revised workflow prioritizes grouping, then approves/declines remaining ungrouped quotes.
    """
    print("Starting approval and grouping process...")

    # Fetch all currently pending quotes for potential grouping
    # Order by ID to maintain some form of document order for the LLM
    all_pending_quotes = db.query(QuoteDB).join(QuoteApprovalDB).filter(QuoteApprovalDB.status == QuoteStatusEnum.PENDING).order_by(QuoteDB.id).all()
    print(f"Found {len(all_pending_quotes)} pending quotes to consider for grouping.")

    if not all_pending_quotes:
        print("No pending quotes to process. Exiting approval and grouping.")
        return

    # 1. Group all pending quotes first
    print("Starting grouping phase for all pending quotes...")
    try:
        prompt = get_formatted_group_quotes_prompt(all_pending_quotes)
        response = get_llm_response(prompt)
        grouped_ids_lists = json.loads(response)

        if not isinstance(grouped_ids_lists, list):
            print("Warning: LLM returned non-list for grouping. Skipping grouping.")
            grouped_ids_lists = [] # Ensure it's iterable

        processed_quote_ids_in_groups = set()
        for group_list in grouped_ids_lists:
            if not isinstance(group_list, list) or len(group_list) < 2:
                continue # Skip invalid or single-quote groups

            # Create a new group
            new_group = QuoteGroupDB(name="LLM-Generated Group", description="Group created by LLM analysis.")
            db.add(new_group)
            db.flush() # To get the new_group.id

            print(f"Created new group {new_group.id} for quotes: {group_list}")

            # Add quotes to the group and update their status to APPROVED
            for quote_id in group_list:
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
        db.commit()
        print("Finished grouping phase. Quotes within groups are now APPROVED.")

    except json.JSONDecodeError:
        print("Error: LLM returned invalid JSON for grouping. Skipping grouping.")
        db.rollback()
    except Exception as e:
        print(f"An error occurred during the grouping phase: {e}")
        db.rollback()

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

    db.commit()
    print("Finished individual approval/decline phase for ungrouped quotes.")
    print("Approval and grouping process complete.")
