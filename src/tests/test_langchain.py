from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.messages import HumanMessage, AIMessage, SystemMessage
from langchain.tools import tool
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver

from langchain_core.utils.uuid import uuid7
from langgraph.types import Command

#from langchain.agents import create_react_agent
import os
# Create config with thread_id for state persistence
config = {"configurable": {"thread_id": str(uuid7())}}

#from langchain.agents import create_react_agent
from langchain_litellm import ChatLiteLLM, LiteLLMEmbeddings
from langchain_litellm import ChatLiteLLMRouter

LITE_LLM_URL = os.getenv("LITE_LLM_URL","http://litellm:4000")
LITE_LLM_API_KEY = os.getenv("LITE_LLM_API_KEY","sk-1234")
model = ChatLiteLLM(
    api_base=LITE_LLM_URL,
    api_key="sk-1234",
    model="openai/llama3.1",
)

# model = ChatLiteLLM(
#     api_base=LITE_LLM_URL,
#     api_key="sk-1234",
#     model="openai/deepseek-flash"
# )
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


msgs2 = {"messages": [{"role": "user", "content": "do 2 things. one. say hi - then invoke print tool"}]}
# for response in agent.stream(msgs2,config=config):
#     print(response)





print(agent.invoke(msgs2,config=config))

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
