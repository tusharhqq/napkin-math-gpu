# modal.Client


```python
class Client(object)
```


## is_closed

```python
is_closed(self)
```
Check if the client is closed.

**Returns**

True if the client is closed, False otherwise.

## hello

```python
hello(self)
```
Connect to server and retrieve version information; raise appropriate error for various failures.

**Usage**

```python
client = modal.Client.from_env()
client.hello()
```

## from_credentials

```python
from_credentials(cls, token_id, token_secret)
```
Constructor based on token credentials; useful for managing Modal on behalf of third-party users.

Also useful when it's necessary to explicitly manage the lifecycle of the client
(e.g. when running Modal in a forked subprocess) — see
[troubleshooting](/docs/guide/troubleshooting#connection-issues-in-forked-processes).

**Parameters**

<Parameter name="token_id" type="str" description="API token ID." />
<Parameter name="token_secret" type="str" description="API token secret." />

**Returns**

An authenticated `Client` with its connection opened.

**Usage**

```python notest
client = modal.Client.from_credentials("my_token_id", "my_token_secret")

modal.Sandbox.create("echo", "hi", client=client, app=app)
```

## get_input_plane_metadata

```python
get_input_plane_metadata(self, input_plane_region)
```
Get the metadata for the input plane.

**Parameters**

<Parameter name="input_plane_region" type="str" description="The region of the input plane." />

**Returns**

The metadata for the input plane as a list of header/value tuples.
