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
    """
    print("Starting approval and grouping process...")

    # 1. Approve or Decline individual quotes
    pending_quotes = db.query(QuoteDB).join(QuoteApprovalDB).filter(QuoteApprovalDB.status == QuoteStatusEnum.PENDING).all()
    print(f"Found {len(pending_quotes)} pending quotes to process.")

    for quote in pending_quotes:
        try:
            prompt = get_formatted_approve_quote_prompt(quote)
            response = get_llm_response(prompt)
            decision = response.strip().upper()

            if decision in ["APPROVED", "DECLINED"]:
                quote.approval.status = QuoteStatusEnum[decision]
                quote.approval.approved_by = "LLM"
                print(f"Quote {quote.id} processed with status: {decision}")
            else:
                print(f"Warning: LLM returned an invalid decision ('{decision}') for quote {quote.id}. Skipping.")

        except Exception as e:
            print(f"Error processing quote {quote.id} for approval: {e}")

    db.commit()
    print("Finished initial approval/decline phase.")

    # 2. Group approved quotes
    print("Starting grouping phase for approved quotes...")
    approved_quotes = db.query(QuoteDB).join(QuoteApprovalDB).filter(QuoteApprovalDB.status == QuoteStatusEnum.APPROVED).order_by(QuoteDB.id).all()
    
    if not approved_quotes:
        print("No approved quotes to group.")
        return

    try:
        prompt = get_formatted_group_quotes_prompt(approved_quotes)
        response = get_llm_response(prompt)
        grouped_ids = json.loads(response)

        if not isinstance(grouped_ids, list):
            print("Warning: LLM returned non-list for grouping. Skipping grouping.")
            return

        for group_list in grouped_ids:
            if not isinstance(group_list, list) or len(group_list) < 2:
                continue
            
            # Create a new group
            new_group = QuoteGroupDB(name="LLM-Generated Group", description="Group created by LLM analysis.")
            db.add(new_group)
            db.flush() # To get the new_group.id

            print(f"Created new group {new_group.id} for quotes: {group_list}")

            # Add quotes to the group
            for quote_id in group_list:
                # Check if quote_id is in the approved_quotes list to be safe
                if any(q.id == quote_id for q in approved_quotes):
                    # Check if the quote is already in a group
                    existing_group_link = db.query(QuoteToGroupDB).filter_by(quote_id=quote_id).first()
                    if not existing_group_link:
                        db.add(QuoteToGroupDB(quote_id=quote_id, group_id=new_group.id))
                    else:
                        print(f"Quote {quote_id} is already in group {existing_group_link.group_id}. Skipping.")
                else:
                    print(f"Warning: LLM returned quote ID {quote_id} for grouping, but it was not in the approved list.")

        db.commit()
        print("Finished grouping phase.")

    except json.JSONDecodeError:
        print("Error: LLM returned invalid JSON for grouping. Skipping grouping.")
    except Exception as e:
        print(f"An error occurred during the grouping phase: {e}")
        db.rollback()

    print("Approval and grouping process complete.")
