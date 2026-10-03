"""OPTIONAL. One call per digest: turns the already-computed aggregate table into 4-5 plain sentences.
Not used for classification. UNTESTED in the submission environment (no API key was available)."""
import os


def narrate(stats, iss_top_md, model="claude-haiku-4-5-20251001"):
    import anthropic  # pip install anthropic
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    prompt = ("You are writing 4-5 plain sentences for a Head of Customer Experience. Use ONLY the numbers below; "
              "do not invent causes. Say what rose, what is big, and what to look at.\n\n"
              f"Week stats: {stats}\n\nIssue table:\n{iss_top_md}")
    r = client.messages.create(model=model, max_tokens=300, messages=[{"role": "user", "content": prompt}])
    return r.content[0].text.strip()
