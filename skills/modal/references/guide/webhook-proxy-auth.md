# Proxy Tokens

Use Proxy Tokens to prevent unauthorized clients from triggering your Web Functions.

```python
import modal

image = modal.Image.debian_slim().pip_install("fastapi")
app = modal.App("proxy-auth-public", image=image)


@app.function()
@modal.fastapi_endpoint()
def public():
    return "hello world"


@app.function()
@modal.fastapi_endpoint(requires_proxy_auth=True)
def private():
    return "hello friend"
```

The `public` endpoint can be hit by any client over the Internet.

```bash
curl https://public-url--goes-here.modal.run
```

The `private` endpoint cannot.

```bash
curl --fail-with-body https://private-url--goes-here.modal.run
# modal-http: missing credentials for proxy authorization
# curl: (22) The requested URL returned error: 401
# https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401
```

Authorization is demonstrated via a Proxy Token. You can create a Proxy Token for your Workspace [here](/settings/proxy-auth-tokens).
In requests to the Web Function, clients supply the Token ID and Token Secret in the `Modal-Key` and `Modal-Secret` HTTP headers.

```bash
export TOKEN_ID=wk-1234abcd
export TOKEN_SECRET=ws-1234abcd
curl -H "Modal-Key: $TOKEN_ID" \
     -H "Modal-Secret: $TOKEN_SECRET" \
     https://private-url--goes-here.modal.run
```

Proxy authorization can be added to [Web Functions](/docs/guide/webhooks) created by the
[`fastapi_endpoint`](/docs/sdk/py/latest/fastapi_endpoint),
[`asgi_app`](/docs/sdk/py/latest/asgi_app),
[`wsgi_app`](/docs/sdk/py/latest/wsgi_app), or
[`web_server`](/docs/sdk/py/latest/web_server) decorators,
which are otherwise publicly available.

Everyone within the Workspace of the Web Function can manage its Proxy Tokens.

## Restricting tokens to specific Environments

On Workspaces with RBAC enabled, tokens can be scoped to specific Environments, restricting which Web Functions they are valid for. See [Proxy tokens for Web Functions](/docs/guide/rbac#proxy-tokens-for-web-functions) in the RBAC guide for more.
