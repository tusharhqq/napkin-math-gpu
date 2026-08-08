# modal.Workspace


```python
class Workspace(modal.object.Object)
```


## hydrate

```python
hydrate(self, client=None)
```
Synchronize the local object with its identity on the Modal server.

It is rarely necessary to call this method explicitly, as most operations
will lazily hydrate when needed. The main use case is when you need to
access object metadata, such as its ID.

*Added in v0.72.39*: This method replaces the deprecated `.resolve()` method.

## name

```python
name(self)
```


## members


```python
members: WorkspaceMembersManager
```

Namespace with methods for managing the membership of a Workspace.


### members.list

```python
list(self)
```
Return the members of the Workspace.

**Examples:**

```python notest
members = modal.Workspace.from_context().members.list()
print([m.name for m in members])
```

## from_context

```python
from_context(*, client=None)
```
Look up the Workspace associated with the current context.

This returns the Workspace that the active Modal credentials authenticate against
(i.e., your active profile or the `MODAL_TOKEN_ID` / `MODAL_TOKEN_SECRET` environment
variables). If called inside a Modal container, it returns the Workspace that the
container is running in.

## billing


```python
billing: WorkspaceBillingManager
```

Namespace for Workspace billing APIs.


### billing.report

```python
report(self, *, start, end=None, resolution="d", tag_names=None)
```
Return a cost report for all Workspace usage, broken down by object and time.

**Parameters**

<Parameter name="start" type="datetime" description="Start of the report, inclusive and rounded to the beginning of the interval. Must be in UTC or timezone-naive (interpreted as UTC)." />
<Parameter name="end" type="datetime | None" defaultValue="None" description="End of the report, exclusive. Must be in UTC or timezone-naive. Partial final intervals will be excluded from the report." />
<Parameter name="resolution" type="str" defaultValue="&quot;d&quot;" description="Resolution, e.g. &quot;d&quot; for daily or &quot;h&quot; for hourly." />
<Parameter name="tag_names" type="list[str] | None" defaultValue="None" description="List of tag names; each row will include the tag name and value in use for that object during the relevant time interval. Pass `[&quot;*&quot;]` to include all tags in the report." />

**Returns**

A list of `BillingReportItem` dataclasses. Each item reports the cost attributed to
a specific Modal object during a given time interval. Cost is further broken down by
the resource type that generated it (e.g. CPU, Memory, specific GPU usage). Note that
the specific resource types included in the breakdown are subject to change as Modal's
billing model evolves.

**See Also**

- [`modal billing report`](https://modal.com/docs/cli/latest/billing#modal-billing-report):
  A workspace report CLI that has convenience features around relative time range queries
  and JSON/CSV output.
- [`Environment.billing.report()`](https://modal.com/docs/sdk/py/latest/modal.Environment#billingreport):
  An analogous report API that is scoped to a specific Environment.

## proxy_tokens


```python
proxy_tokens: WorkspaceProxyTokenManager
```

Namespace with methods for managing the proxy tokens in a Workspace.

See [the guide](https://modal.com/docs/guide/webhook-proxy-auth) for more information on proxy tokens.


### proxy_tokens.create

```python
create(self)
```
Create a new proxy token for the Workspace.

**Usage**

```python notest
token = modal.Workspace.from_context().proxy_tokens.create()
print(token.token_id, token.token_secret)
```

### proxy_tokens.list

```python
list(self, environment_name=None)
```
List proxy tokens in the Workspace.

**Parameters**

<Parameter name="environment_name" type="Optional[str]" defaultValue="None" description="When provided, list only the tokens associated with this environment." />

**Usage**

```python notest
ws = modal.Workspace.from_context()

# List all proxy tokens in the Workspace
tokens = ws.proxy_tokens.list()
print([t.token_id for t in tokens])

# List only the proxy tokens associated with a specific Environment
env_tokens = ws.proxy_tokens.list(environment_name="prod")
```

### proxy_tokens.allow

```python
allow(self, proxy_token_id, environment_name)
```
Allow a proxy token to authenticate requests to a given Environment.

**Parameters**

<Parameter name="proxy_token_id" type="str" description="The token ID (`wk-...`) to operate on." />
<Parameter name="environment_name" type="str" description="The name of the environment to allow access to." />

**Usage**

```python notest
ws = modal.Workspace.from_context()
token = ws.proxy_tokens.create()
ws.proxy_tokens.allow(token.token_id, "prod")
```

### proxy_tokens.revoke

```python
revoke(self, proxy_token_id, environment_name)
```
Revoke a proxy token's access to a given Environment.

The proxy token is not deleted, and it will continue to authenticate requests to any
other Environments it is associated with.

**Parameters**

<Parameter name="proxy_token_id" type="str" description="The token ID (`wk-...`) to operate on." />
<Parameter name="environment_name" type="str" description="The name of the environment to revoke access from." />

**Usage**

```python notest
ws = modal.Workspace.from_context()
ws.proxy_tokens.revoke(token_id, "prod")
```

### proxy_tokens.delete

```python
delete(self, proxy_token_id)
```
Delete a proxy token from the Workspace.

This cannot be reverted. Any clients currently using the token will immediately
lose access to associated resources.

**Parameters**

<Parameter name="proxy_token_id" type="str" description="The token ID (`wk-...`) to delete." />

**Usage**

```python notest
modal.Workspace.from_context().proxy_tokens.delete(token_id)
```

## settings


```python
settings: WorkspaceSettingsManager
```

Namespace for Workspace settings APIs.


### settings.valid_settings

```python
valid_settings(cls)
```


### settings.list

```python
list(self)
```
Return a the current workspace settings.

**Returns**

A `WorkspaceSettings` dataclass.

### settings.set

```python
set(self, name, value)
```
Set a workspace setting to a new value. Must be workspace manager or owner.

The following settings can be updated:

- image-builder-version: The image builder version determines the software included in our base images.
- default-environment: The default environment when the environment is omitted from SDK or CLI methods.

**Parameters**

<Parameter name="name" type="str" description="The name of the setting." />
<Parameter name="value" type="str" description="The new value of the setting." />

**Usage**

```python notest
modal.Workspace.from_context().settings.set("default-environment", "dev")
```
