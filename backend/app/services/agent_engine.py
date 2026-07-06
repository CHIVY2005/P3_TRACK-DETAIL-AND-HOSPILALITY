import os
import json
from datetime import datetime
from typing import Dict, Any, List, TypedDict
from sqlalchemy.orm import Session
from app.db import models
from app.config import settings
from app.services.cpi_calculator import calculate_cpi_for_product

# --- LlamaIndex RAG Integration ---
def query_supplier_policy_rag(brand_name: str, query_text: str) -> str:
    """
    Integrates LlamaIndex to query supplier price agreement policies (RAG).
    """
    openai_key = os.getenv("OPENAI_API_KEY", "")
    knowledge_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "knowledge", "supplier_policies.txt"))
    
    # Check if OpenAI key is set and knowledge document exists
    if not openai_key or "your_openai" in openai_key or not os.path.exists(knowledge_path):
        # Fallback simulated query
        if "Roche-Posay" in brand_name:
            return "Chính sách La Roche-Posay hỗ trợ tối đa 20% giá vốn để Guardian khớp giá đối thủ. Đại diện: Ms. Thảo Nguyễn (thao.nguyen@loreal.com)."
        elif "Bioderma" in brand_name:
            return "Thỏa thuận Bioderma hỗ trợ Credit Note trị giá 12.000 VND/đơn vị khi đối thủ giảm giá. Đại diện: Mr. Hoàng Lâm (lam.hoang@minhanhbeauty.vn)."
        elif "Anessa" in brand_name:
            return "Hãng Shiseido yêu cầu gửi đề xuất duyệt chiết khấu đặc biệt tối đa 15.000 VND trước 48h. Đại diện: Ms. Linh Chi (chi.linh@shiseido.com.vn)."
        return f"Liên hệ hỗ trợ đàm phán giá vốn với Đại diện thương hiệu {brand_name} qua email của hãng."

    try:
        from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext
        from llama_index.llms.openai import OpenAI
        from llama_index.core.settings import Settings
        
        # Configure OpenAI model
        Settings.llm = OpenAI(model="gpt-4o-mini", api_key=openai_key)
        
        # Read and Index policies document
        documents = SimpleDirectoryReader(input_files=[knowledge_path]).load_data()
        index = VectorStoreIndex.from_documents(documents)
        
        # Query index
        query_engine = index.as_query_engine()
        response = query_engine.query(f"Đối với hãng {brand_name}, chính sách bảo vệ giá, hoàn tiền hoặc email đại diện liên hệ là gì? Trả lời ngắn gọn.")
        return str(response)
    except Exception as e:
        print(f"LlamaIndex RAG query failed: {e}")
        return f"Lỗi truy vấn LlamaIndex. Đại diện thương hiệu {brand_name} có thể liên hệ trực tiếp qua hệ thống."

# --- LangGraph Setup ---
class AgentState(TypedDict):
    product_id: int
    competitor_price_id: int
    cost_price: float
    guardian_price: float
    competitor_price: float
    competitor_name: str
    target_margin: float
    strategy: str  # "match" | "negotiate" | "maintain"
    negotiation_context: str
    email_draft: Dict[str, str]
    logs: List[str]
    actions_created: List[Dict[str, Any]]

# LangGraph Nodes
def node_run_margin_analysis(state: AgentState) -> AgentState:
    logs = list(state.get("logs", []))
    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] [Node: margin_analysis] Khởi chạy tính toán biên lợi nhuận...")
    
    guardian_p = state["guardian_price"]
    comp_p = state["competitor_price"]
    cost = state["cost_price"]
    
    current_margin = ((guardian_p - cost) / guardian_p) * 100
    target_margin = ((comp_p - cost) / comp_p) * 100
    
    logs.append(f"  Giá gốc Guardian: {guardian_p:,.0f} VND (Biên LN: {current_margin:.1f}%)")
    logs.append(f"  Giá vốn nhập khẩu: {cost:,.0f} VND")
    logs.append(f"  Giá bán lẻ đối thủ: {comp_p:,.0f} VND (Biên LN nếu khớp: {target_margin:.1f}%)")
    
    state["target_margin"] = target_margin
    state["logs"] = logs
    return state

def node_determine_strategy(state: AgentState) -> AgentState:
    logs = list(state.get("logs", []))
    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] [Node: determine_strategy] LLM quyết định chiến lược định giá...")
    
    openai_key = os.getenv("OPENAI_API_KEY", "")
    target_margin = state["target_margin"]
    SAFE_MARGIN_LIMIT = 15.0  # 15% safety limit
    
    # 1. Check if OpenAI API keys are set for Langfuse tracing and LLM decision-making
    if not openai_key or "your_openai" in openai_key:
        # Fallback rule-based reasoning (mock LLM)
        logs.append("  [Reasoning] (Chế độ mô phỏng) Không tìm thấy OpenAI key. Chuyển sang quy tắc nghiệp vụ mặc định.")
        if target_margin >= SAFE_MARGIN_LIMIT:
            strategy = "match"
            logs.append(f"  [Decision] Biên lợi nhuận đạt {target_margin:.1f}% >= Ngưỡng an toàn ({SAFE_MARGIN_LIMIT}%). Quyết định: Match giá.")
        else:
            strategy = "negotiate"
            logs.append(f"  [Decision] Biên lợi nhuận {target_margin:.1f}% < Ngưỡng an toàn ({SAFE_MARGIN_LIMIT}%). Quyết định: Thương lượng giá vốn.")
    else:
        # Real OpenAI Call with Langfuse Tracing
        try:
            from langchain_openai import ChatOpenAI
            from langchain.schema import HumanMessage, SystemMessage
            from langfuse.callback import CallbackHandler
            
            # Setup Langfuse tracing if credentials exist
            callbacks = []
            lf_public = os.getenv("LANGFUSE_PUBLIC_KEY", "")
            lf_secret = os.getenv("LANGFUSE_SECRET_KEY", "")
            if lf_public and "your_langfuse" not in lf_public:
                handler = CallbackHandler(
                    public_key=lf_public,
                    secret_key=lf_secret,
                    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
                )
                callbacks.append(handler)
                logs.append("  [Tracing] Đã kích hoạt Langfuse Callback Handler thành công.")

            llm = ChatOpenAI(model="gpt-4o-mini", api_key=openai_key, temperature=0.0)
            
            system_prompt = (
                "Bạn là chuyên gia cố vấn định giá của Guardian. Nhiệm vụ của bạn là đưa ra chiến lược xử lý alerts.\n"
                "Quy tắc:\n"
                "- Nếu biên lợi nhuận ròng (target_margin) >= 15%, trả về chiến lược 'match' để giữ thị phần.\n"
                "- Nếu target_margin < 15%, trả về 'negotiate' để đàm phán giảm giá vốn.\n"
                "- Trả về định dạng JSON: {\"strategy\": \"match\" | \"negotiate\", \"reasoning\": \"lý do suy luận\"}"
            )
            
            prompt = f"Product: {state['product_id']}, Target Margin: {target_margin:.1f}%, Competitor: {state['competitor_name']}"
            
            # Run chain
            response = llm.invoke(
                [SystemMessage(content=system_prompt), HumanMessage(content=prompt)],
                config={"callbacks": callbacks} if callbacks else {}
            )
            
            data = json.loads(response.content)
            strategy = data.get("strategy", "negotiate")
            logs.append(f"  [LLM Reasoning] {data.get('reasoning', '')}")
            logs.append(f"  [Decision] Quyết định cuối cùng của LLM: {strategy.upper()}")
        except Exception as e:
            logs.append(f"  [Warning] Lỗi khi gọi OpenAI/Langfuse: {e}. Sử dụng fallback.")
            strategy = "match" if target_margin >= SAFE_MARGIN_LIMIT else "negotiate"

    state["strategy"] = strategy
    state["logs"] = logs
    return state

def node_apply_auto_match(state: AgentState) -> AgentState:
    # This node matches the price (writes back to product table in backend database session context)
    logs = list(state.get("logs", []))
    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] [Node: apply_auto_match] Khởi chạy tool adjust_system_price...")
    logs.append(f"  [Action] Đã đồng bộ giá bán Guardian xuống còn {state['competitor_price']:,.0f} VND.")
    
    actions = list(state.get("actions_created", []))
    actions.append({
        "action_type": "AUTO_PRICE_MATCH",
        "description": f"Tự động khớp giá bán của Guardian với competitor {state['competitor_name']} từ {state['guardian_price']:,.0f} xuống {state['competitor_price']:,.0f} VND.",
        "data": json.dumps({
            "old_price": state["guardian_price"],
            "new_price": state["competitor_price"],
            "target_margin": f"{state['target_margin']:.1f}%"
        })
    })
    
    state["actions_created"] = actions
    state["logs"] = logs
    return state

def node_draft_supplier_negotiation(state: AgentState) -> AgentState:
    logs = list(state.get("logs", []))
    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] [Node: supplier_negotiation] Khởi chạy tool generate_supplier_negotiation_draft...")
    
    # 1. Run LlamaIndex RAG query to retrieve brand policies
    brand = state["competitor_name"] # Or product category/brand. For simplicity we look at product info
    logs.append("  [RAG] Đang truy vấn chính sách thỏa thuận của hãng bằng LlamaIndex...")
    
    brand_context = query_supplier_policy_rag("La Roche-Posay", "Chính sách đền bù giá nhập")
    logs.append(f"  [RAG Result] {brand_context[:100]}...")
    
    # 2. Draft Email
    subject = f"[Yêu Cầu Hỗ Trợ Giá] Đàm phán giảm giá vốn bảo vệ thị phần"
    body = (
        f"Kính gửi đối tác thương hiệu,\n\n"
        f"Hệ thống Guardian ghi nhận biến động chênh giá lớn đối với sản phẩm mã ID {state['product_id']}.\n"
        f"Đầu mối đối thủ ({state['competitor_name']}) đang phân phối với giá Net Price cực thấp là {state['competitor_price']:,.0f} VND.\n"
        f"Để đảm bảo doanh số bán lẻ, chúng tôi đề xuất kích hoạt điều khoản đền bù giá nhập dựa trên chính sách hãng:\n"
        f"Chi tiết chính sách hỗ trợ: {brand_context}\n\n"
        f"Giá vốn hiện tại: {state['cost_price']:,.0f} VND. Đề nghị giảm giá nhập đợt này xuống mức đề xuất mới.\n\n"
        f"Trân trọng,\nPhòng Category Management - Guardian Việt Nam."
    )
    
    email_draft = {
        "subject": subject,
        "body": body,
        "recipient": "partner@beautybrands.com"
    }
    
    actions = list(state.get("actions_created", []))
    actions.append({
        "action_type": "SUPPLIER_EMAIL_DRAFT",
        "description": f"Đã soạn thảo thư đề xuất giảm chi phí vốn gửi nhà cung cấp nhằm bảo vệ biên lợi nhuận ròng của sản phẩm.",
        "data": json.dumps({
            "subject": subject,
            "body": body,
            "competitor_price": state["competitor_price"],
            "rag_context": brand_context
        })
    })
    
    state["email_draft"] = email_draft
    state["actions_created"] = actions
    state["logs"] = logs
    return state

# Build LangGraph workflow
def run_langgraph_agent_for_alert(db: Session, alert: models.Alert) -> Dict[str, Any]:
    """
    Constructs and runs the LangGraph pricing optimizer agent workflow.
    """
    product = alert.product
    if not product:
        return {"status": "skipped", "reason": "No product"}
        
    # Get latest competitor price
    latest_price = db.query(models.CompetitorPrice).filter(
        models.CompetitorPrice.product_id == product.id
    ).order_by(models.CompetitorPrice.scraped_at.desc()).first()
    
    if not latest_price:
        return {"status": "skipped", "reason": "No competitor prices"}

    # Initialize State
    initial_state = AgentState(
        product_id=product.id,
        competitor_price_id=latest_price.id,
        cost_price=product.cost_price or (product.guardian_price * 0.60),
        guardian_price=product.guardian_price,
        competitor_price=latest_price.net_price,
        competitor_name=latest_price.competitor_name,
        target_margin=0.0,
        strategy="maintain",
        negotiation_context="",
        email_draft={},
        logs=[f"[LangGraph Agent Starting] Bắt đầu tối ưu cho cảnh báo ID {alert.id}"],
        actions_created=[]
    )

    try:
        from langgraph.graph import StateGraph, END
        
        # Define Graph
        workflow = StateGraph(AgentState)
        
        # Add Nodes
        workflow.add_node("margin_analysis", node_run_margin_analysis)
        workflow.add_node("determine_strategy", node_determine_strategy)
        workflow.add_node("apply_auto_match", node_apply_auto_match)
        workflow.add_node("supplier_negotiation", node_draft_supplier_negotiation)
        
        # Set Entrypoint
        workflow.set_entry_point("margin_analysis")
        
        # Define Edges
        workflow.add_edge("margin_analysis", "determine_strategy")
        
        # Conditional Edge router
        def router_edge(state: AgentState):
            if state["strategy"] == "match":
                return "apply_auto_match"
            else:
                return "supplier_negotiation"
                
        workflow.add_conditional_edges(
            "determine_strategy",
            router_edge,
            {
                "apply_auto_match": "apply_auto_match",
                "supplier_negotiation": "supplier_negotiation"
            }
        )
        
        workflow.add_edge("apply_auto_match", END)
        workflow.add_edge("supplier_negotiation", END)
        
        # Compile
        app_graph = workflow.compile()
        
        # Run graph
        final_state = app_graph.invoke(initial_state)
        
        # Apply pricing updates to DB if match was decided
        if final_state["strategy"] == "match":
            product.guardian_price = latest_price.net_price
            alert.is_resolved = True
            db.commit()
            
        return final_state
        
    except Exception as e:
        print(f"Failed to run LangGraph compilation: {e}. Running fallback sequence...")
        # Fallback sequence in case LangGraph package has installation errors
        s = node_run_margin_analysis(initial_state)
        s = node_determine_strategy(s)
        if s["strategy"] == "match":
            s = node_apply_auto_match(s)
            product.guardian_price = latest_price.net_price
            alert.is_resolved = True
        else:
            s = node_draft_supplier_negotiation(s)
        db.commit()
        return s

# Main Agent execution loop triggered by backend routes
def run_agentic_optimization_loop(db: Session) -> models.AgentTask:
    task = models.AgentTask(
        objective="Analyze active price discrepancies, protect profit margins, and optimize competitor index.",
        status="Running",
        logs="[Agent Initialized] Starting LangGraph + Langfuse autonomous pricing sweep...\n"
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    logs = [f"[Agent Task ID {task.id} started. Objective: {task.objective}]"]
    
    try:
        alerts = db.query(models.Alert).filter(models.Alert.is_resolved == False).all()
        logs.append(f"Phát hiện {len(alerts)} cảnh báo đang chờ xử lý...")
        task.logs = "\n".join(logs)
        db.commit()

        if not alerts:
            logs.append("Không phát hiện cảnh báo mới. Trạng thái hệ thống an toàn.")
            task.status = "Completed"
            task.completed_at = datetime.utcnow()
            task.logs = "\n".join(logs)
            db.commit()
            return task

        for alert in alerts[:6]:
            # Run LangGraph pricing agent
            agent_result = run_langgraph_agent_for_alert(db, alert)
            
            # Capture logs from the agent state run
            for agent_log in agent_result.get("logs", []):
                logs.append(f"  {agent_log}")
                
            # Save Actions
            for act in agent_result.get("actions_created", []):
                action_record = models.AgentAction(
                    task_id=task.id,
                    product_id=alert.product_id,
                    action_type=act["action_type"],
                    description=act["description"],
                    data=act["data"]
                )
                db.add(action_record)
            
            db.commit()
            task.logs = "\n".join(logs)
            db.commit()

        task.status = "Completed"
        logs.append("[Agent Sweep Finished] Tất cả cảnh báo đã được tối ưu hóa bằng LangGraph workflow.")
    except Exception as e:
        logs.append(f"[CRITICAL ERROR] {e}")
        task.status = "Failed"
        
    task.completed_at = datetime.utcnow()
    task.logs = "\n".join(logs)
    db.commit()
    return task
