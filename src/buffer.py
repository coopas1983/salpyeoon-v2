import os
import requests

API = "https://api.buffer.com"


def gql(query: str, variables: dict | None = None):
    key = os.environ["BUFFER_API_KEY"]
    r = requests.post(
        API,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"query": query, "variables": variables or {}},
        timeout=30,
    )
    r.raise_for_status()
    payload = r.json()
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    return payload.get("data", {})


def organizations():
    q = '''query { account { organizations { id name } } }'''
    return gql(q)["account"]["organizations"]


def list_channels():
    out = []
    for org in organizations():
        q = '''query($id: OrganizationId!) { channels(input:{organizationId:$id}) { id name displayName service isDisconnected isLocked } }'''
        for c in gql(q, {"id": org["id"]}).get("channels", []):
            c["organizationId"] = org["id"]
            out.append(c)
    return out


def threads_channel():
    for c in list_channels():
        if c.get("service") == "threads" and not c.get("isDisconnected") and not c.get("isLocked"):
            return c
    raise RuntimeError("No usable Threads channel in Buffer")


def create_text_post(channel_id: str, text: str, mode="shareNow", save_to_draft=False):
    q = '''mutation($input: CreatePostInput!) {
      createPost(input:$input) {
        ... on PostActionSuccess { post { id text status dueAt } }
        ... on MutationError { message }
      }
    }'''
    inp = {"text": text, "channelId": channel_id, "schedulingType": "automatic", "mode": mode}
    if save_to_draft:
        inp["saveToDraft"] = True
    data = gql(q, {"input": inp})
    result = data.get("createPost", {})
    if result.get("post", {}).get("id"):
        return result["post"]
    raise RuntimeError(f"Buffer createPost failed: {result.get('message') or result}")


def sent_posts_with_metrics(limit: int = 50):
    ch = threads_channel()
    q = '''query($org: OrganizationId!, $channels: [ChannelId!], $first: Int!) {
      posts(first:$first, input:{organizationId:$org, filter:{status:[sent], channelIds:$channels}}) {
        edges { node { id text dueAt channelId metrics { type name value unit } metricsUpdatedAt } }
      }
    }'''
    data = gql(q, {"org": ch["organizationId"], "channels": [ch["id"]], "first": limit})
    return [e["node"] for e in data.get("posts", {}).get("edges", [])]
