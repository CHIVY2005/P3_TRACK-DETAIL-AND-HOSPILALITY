import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.db import models
from app.services.cpi_calculator import calculate_cpi_for_product

def run_agentic_optimization_loop(db: Session) -> models.AgentTask:
    """
    Simulates an autonomous AI Pricing Agent that runs a loop:
    1. Detects pricing discrepancies (Alerts)
    2. Analyses profit margins (Tool: calculate_margin)
    3. Takes actions (Tool: adjust_price OR Tool: draft_supplier_email)
    4. Logs thoughts, observations, and decisions.
    """
    # 1. Create a new Agent Task
    task = models.AgentTask(
        objective="Analyze active price discrepancies, protect profit margins, and optimize competitor index.",
        status="Running",
        logs="[Agent Initialized] Starting autonomous competitive pricing sweep...\n"
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    logs = []
    def log(msg: str):
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
        task.logs = "\n".join(logs)
        db.commit()

    log(f"Agent Task ID {task.id} started. Objective: {task.objective}")
    
    try:
        # Fetch all unresolved alerts (excluding resolved ones)
        alerts = db.query(models.Alert).filter(models.Alert.is_resolved == False).all()
        log(f"Scanning system... Found {len(alerts)} active alerts requiring attention.")

        if not alerts:
            log("No active pricing anomalies detected. Guardian's pricing is within safe bounds.")
            task.status = "Completed"
            task.completed_at = datetime.utcnow()
            db.commit()
            return task

        # Process up to 5 alerts in this agent run to simulate paced decision-making
        processed_count = 0
        for alert in alerts[:6]:
            product = alert.product
            if not product:
                continue

            log(f"--- Processing Product: '{product.name}' (Barcode: {product.barcode}) ---")
            log(f"Reasoning: Detected alert '{alert.alert_type}' with severity '{alert.severity}'. Message: '{alert.message}'")
            
            # Find latest competitor prices for this product to identify the competitor undercutting us
            latest_price_records = db.query(models.CompetitorPrice).filter(
                models.CompetitorPrice.product_id == product.id
            ).order_by(models.CompetitorPrice.scraped_at.desc()).all()
            
            if not latest_price_records:
                log(f"Observation: No recent competitor pricing data. Skipping product.")
                continue

            # Identify the cheapest competitor
            cheapest_comp = min(latest_price_records, key=lambda x: x.net_price)
            log(f"Observation: Cheapest competitor is {cheapest_comp.competitor_name} selling at {cheapest_comp.net_price:,.0f} VND (Guardian price: {product.guardian_price:,.0f} VND).")

            # --- Tool 1: Calculate Margin ---
            log(f"Tool Call: margin_calculator(product_id={product.id}, target_price={cheapest_comp.net_price:,.0f})")
            
            cost = product.cost_price or (product.guardian_price * 0.60) # fallback cost if not set
            current_margin = ((product.guardian_price - cost) / product.guardian_price) * 100
            target_margin = ((cheapest_comp.net_price - cost) / cheapest_comp.net_price) * 100
            
            log(f"Observation: Cost price is {cost:,.0f} VND. Current margin: {current_margin:.1f}%. Target margin if matched: {target_margin:.1f}%.")

            # Decision criteria
            SAFE_MARGIN_THRESHOLD = 15.0 # 15% minimum acceptable margin

            if target_margin >= SAFE_MARGIN_THRESHOLD:
                # We can match! Action: Adjust System Price
                log(f"Decision: Target margin ({target_margin:.1f}%) is above safety threshold ({SAFE_MARGIN_THRESHOLD}%). Matching price.")
                
                # --- Tool 2: Adjust System Price ---
                old_price = product.guardian_price
                new_price = cheapest_comp.net_price
                
                log(f"Tool Call: adjust_system_price(product_id={product.id}, new_price={new_price:,.0f})")
                product.guardian_price = new_price
                db.commit()
                
                # Recalculate CPI after price change
                calculate_cpi_for_product(db, product.id)
                
                # Log action to DB
                action = models.AgentAction(
                    task_id=task.id,
                    product_id=product.id,
                    action_type="AUTO_PRICE_MATCH",
                    description=f"Auto-matched price of '{product.name}' to competitor {cheapest_comp.competitor_name} (from {old_price:,.0f} to {new_price:,.0f} VND).",
                    data=json.dumps({
                        "competitor": cheapest_comp.competitor_name,
                        "old_price": old_price,
                        "new_price": new_price,
                        "cost": cost,
                        "result_margin": f"{target_margin:.1f}%"
                    })
                )
                db.add(action)
                
                # Auto-resolve the alert since we adjusted price
                alert.is_resolved = True
                db.commit()
                log(f"Observation: Successfully updated price. Pricing Index updated, original alert marked as resolved.")

            else:
                # We cannot match. Margin too low! Action: Draft Supplier Negotiation Email
                log(f"Decision: Matching would reduce margin to {target_margin:.1f}% (below safety limit {SAFE_MARGIN_THRESHOLD}%). Initiating cost support request.")
                
                # --- Tool 3: Draft Supplier Negotiation Email ---
                log(f"Tool Call: generate_supplier_negotiation_draft(product_id={product.id}, competitor_price={cheapest_comp.net_price:,.0f})")
                
                email_subject = f"[Yêu Cầu Hỗ Trợ Giá] Bảo vệ thị phần sản phẩm {product.name}"
                email_body = f"""Kính gửi quý Đối tác / Nhà Cung Cấp,

Hệ thống giám sát giá tự động của Guardian ghi nhận biến động giá lớn của sản phẩm:
- Tên sản phẩm: {product.name}
- Barcode: {product.barcode}
- Giá bán hiện tại của Guardian: {product.guardian_price:,.0f} VND
- Giá bán thấp nhất của đối thủ ({cheapest_comp.competitor_name}): {cheapest_comp.net_price:,.0f} VND

Để duy trì thị phần và cạnh tranh công bằng trên các sàn thương mại điện tử, Guardian đề xuất điều chỉnh giá nhập (cost price) giảm tương ứng để đảm bảo biên lợi nhuận mục tiêu. 

Chi tiết đề xuất:
- Giá nhập hiện tại: {cost:,.0f} VND
- Giá nhập đề xuất mới: {round(cheapest_comp.net_price * 0.65, -3):,.0f} VND

Rất mong Quý đối tác sớm phản hồi và hỗ trợ.
Trân trọng,
Đội ngũ Category Management - Guardian Việt Nam."""

                # Log action to DB
                action = models.AgentAction(
                    task_id=task.id,
                    product_id=product.id,
                    action_type="SUPPLIER_EMAIL_DRAFT",
                    description=f"Drafted cost protection negotiation proposal to supplier for product '{product.name}'. Target purchase cost reduction: {(cost - round(cheapest_comp.net_price * 0.65, -3)):,.0f} VND.",
                    data=json.dumps({
                        "subject": email_subject,
                        "body": email_body,
                        "competitor": cheapest_comp.competitor_name,
                        "competitor_price": cheapest_comp.net_price,
                        "cost": cost
                    })
                )
                db.add(action)
                db.commit()
                log(f"Observation: Negotiation draft written successfully. Supplier account manager notified.")
            
            processed_count += 1
            
        log(f"Loop completed. Processed {processed_count} alerts in this run.")
        task.status = "Completed"
        
    except Exception as e:
        log(f"CRITICAL ERROR in Agent Engine: {str(e)}")
        task.status = "Failed"
        
    task.completed_at = datetime.utcnow()
    db.commit()
    return task
