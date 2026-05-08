from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.messages import HumanMessage, AIMessage, SystemMessage
from langchain.tools import tool
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver

from langchain_core.utils.uuid import uuid7
from langgraph.types import Command

from langchain.agents import create_react_agent

# Create config with thread_id for state persistence
config = {"configurable": {"thread_id": str(uuid7())}}

model = ChatOpenAI(
    base_url="https://opencode.ai/zen/go/v1",
    api_key="",
    model="deepseek-v4-flash",
    reasoning_effort="low"
)
@tool
def print_hello() -> str:
    """prints hello and returns hello as a string. Used as a test tool"""
    print("hello")
    return "hello"


# Checkpointer is REQUIRED for human-in-the-loop
checkpointer = MemorySaver()

agent = create_deep_agent(
    model=model,
    tools=[print_hello],
    interrupt_on={
        "print_hello": False,  # Default: approve, edit, reject, respond
       # "read_file": False,   # No interrupts needed
       # "send_email": {"allowed_decisions": ["approve", "reject"]},  # No editing
    },
    checkpointer=checkpointer  # Required!
)


#ef run_turn(turn, messages):
    #sub_turn = 1
   # while True:
        
        # messages.append(response.choices[0].message)
        # reasoning_content = response.choices[0].message.reasoning_content
        # content = response.choices[0].message.content
        # tool_calls = response.choices[0].message.tool_calls
        # print(f"Turn {turn}.{sub_turn}\n{reasoning_content=}\n{content=}\n{tool_calls=}")
        #break
        # # If there is no tool calls, then the model should get a final answer and we need to stop the loop
        # if tool_calls is None:
        #     break
        # for tool in tool_calls:
        #     tool_function = TOOL_CALL_MAP[tool.function.name]
        #     tool_result = tool_function(**json.loads(tool.function.arguments))
        #     print(f"tool result for {tool.function.name}: {tool_result}\n")
        #     messages.append({
        #         "role": "tool",
        #         "tool_call_id": tool.id,
        #         "content": tool_result,
        #     })
        # sub_turn += 1
    #print()



# The user starts a question
turn = 1
messages = [{
    "role": "user",
    "content": "do 2 things. one. say hi - then invoke print tool"
}]
msgs2 = {"messages": [{"role": "user", "content": "do 2 things. one. say hi - then invoke print tool"}]}
# for response in agent.stream(msgs2,config=config):
#     print(response)





for chunk in agent.stream(
    msgs2,
    stream_mode="messages",
    config=config,
    version="v2",
):
    if chunk["type"] == "messages":
        token, metadata = chunk["data"]

        # Identify source: "main" or the subagent namespace segment
        is_subagent = any(s.startswith("tools:") for s in chunk["ns"])
        source = next((s for s in chunk["ns"] if s.startswith("tools:")), "main") if is_subagent else "main"

        # Tool call chunks (streaming tool invocations)
        if token.tool_call_chunks:
            for tc in token.tool_call_chunks:
                if tc.get("name"):
                    print(f"\n[{source}] Tool call: {tc['name']}")
                # Args stream in chunks - write them incrementally
                if tc.get("args"):
                    print(tc["args"], end="", flush=True)

        # Tool results
        if token.type == "tool":
            print(f"\n[{source}] Tool result [{token.name}]: {str(token.content)[:150]}")

        # Regular AI content (skip tool call messages)
        if token.type == "ai" and token.content and not token.tool_call_chunks:
            print(token.content, end="", flush=True)

print()


# The user starts a new question
# turn = 2
# messages.append({
#     "role": "user",
#     "content": "How's the weather in Guangzhou Tomorrow"
# })
# run_turn(turn, messages)


# system_msg = SystemMessage("You are a helpful assistant.")
# human_msg = HumanMessage("invoke the print hello tool")
# messages = [system_msg, human_msg]

# while True:

#     response = agent.stream(
#         {"messages": [{"role": "user", "content": "do 2 things. one. say hi - then invoke print tool"}]},
#         config=config
#     )


# # # Use with chat models
# #gent = create_agent(model)
# # # res  = agent.invoke("say hi. nothing else")
# # # print(res)

# # messages = [system_msg, human_msg]
# # response = model.invoke(messages)  
# print(response)