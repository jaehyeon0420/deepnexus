from langgraph.graph import StateGraph, END
from app.schemas.model import AgentState
from app.graph.nodes import router_node, sql_agent_node, vector_search_node, generator_node

def build_graph():
    workflow = StateGraph(AgentState)
    
    # 각 작업 담당 노드 추가. (정형/비정형 경로 설정 -> 정형 데이터 처리 -> 비정형 데이터 처리 -> 최종 답변 생성)
    workflow.add_node("router", router_node)
    workflow.add_node("sql_agent", sql_agent_node)
    workflow.add_node("vector_search", vector_search_node)
    workflow.add_node("generator", generator_node)
    
    # 시작점
    workflow.set_entry_point("router")
    
    # 조건부 엣지 (Router의 결정에 따라 분기. 리스트 반환 시 병렬 실행)
    def route_decision(state: AgentState):
        intent = state["intent"]
        print(f"Router 결과 : {intent}")
        if intent == "rdb":
            return ["sql_agent"]
        elif intent == "vector":
            return ["vector_search"]
        elif intent == "both":
            return ["sql_agent", "vector_search"] # 병렬 실행
        else : 
            return ["generator"]
            
    workflow.add_conditional_edges(
        "router",
        route_decision,
        {
            "sql_agent": "sql_agent", 
            "vector_search": "vector_search",
            "generator": "generator"
        }
    )
    
    # 병렬 실행 후 Generator로 모음
    workflow.add_edge("sql_agent", "generator")
    workflow.add_edge("vector_search", "generator")
    
    # 종료
    workflow.add_edge("generator", END)
    
    return workflow.compile()

app_graph = build_graph()