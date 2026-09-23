from dotenv import load_dotenv   # a tool that reads the .env file
import anthropic                  # Claude's library

load_dotenv()                     # load .env into environment variables

client = anthropic.Anthropic()    # creates a connection; finds ANTHROPIC_API_KEY automatically

response = client.messages.create(
    model="claude-haiku-4-5",      # which AI model to use
    max_tokens=300,               # the longest reply we'll allow (limits cost)
    messages=[                    # the conversation so far: a list of messages
        {"role": "user", "content": "Are you ready to help me?"}
    ],
)

response1 = client.messages.create(
    model = "claude-haiku-4-5",
    max_tokens = 150,
    messages = [{"role": "user", "content": "My favorite drive brand is Western Digital. Say OK"}],
)
response2 = client.messages.create(
    model = "claude-haiku-4-5",
    max_tokens = 150,
    messages = [
    {"role": "user","content": "My favorite drive brand is Western Digital. Say OK"},
    {"role":"assistant", "content": response1.content[0].text},
    {"role": "user", "content": "What's my favorite drive brand?"}],
)

print(response2.content[0].text)   # the reply's text
print(response1.usage)
print(response2.usage)
