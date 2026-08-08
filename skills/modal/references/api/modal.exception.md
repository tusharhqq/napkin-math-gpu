# modal.exception

Modal-specific exception types.

## Notes on `grpclib.GRPCError` migration

Historically, the Modal SDK could propagate `grpclib.GRPCError` exceptions out
to user code.  As of v1.3, we are in the process of gracefully migrating to
always raising a Modal exception type in these cases. To avoid breaking user
code that relies on catching `grpclib.GRPCError`, a subset of Modal exception
types temporarily inherit from `grpclib.GRPCError`.

We encourage users to migrate any code that currently catches `grpclib.GRPCError`
to instead catch the appropriate Modal exception type. The following mapping
between GRPCError status codes and Modal exception types is currently in use:

```
CANCELLED -> ServiceError
UNKNOWN -> ServiceError
INVALID_ARGUMENT -> InvalidError
DEADLINE_EXCEEDED -> ServiceError
NOT_FOUND -> NotFoundError
ALREADY_EXISTS -> AlreadyExistsError
PERMISSION_DENIED -> PermissionDeniedError
RESOURCE_EXHAUSTED -> ResourceExhaustedError
FAILED_PRECONDITION -> ConflictError
ABORTED -> ConflictError
OUT_OF_RANGE -> InvalidError
UNIMPLEMENTED -> UnimplementedError
INTERNAL -> InternalError
UNAVAILABLE -> ServiceError
DATA_LOSS -> DataLossError
UNAUTHENTICATED -> AuthError
```

## modal.exception.AlreadyExistsError


```python
class AlreadyExistsError(modal.exception.Error, modal.exception._GRPCErrorWrapper)
```

Raised when a resource creation conflicts with an existing resource.

```python
__init__(self, message=None)
```


### message

```python
message(self)
```


### status

```python
status(self)
```


### details

```python
details(self)
```

## modal.exception.AsyncUsageWarning


```python
class AsyncUsageWarning(UserWarning)
```

Warning emitted when a blocking Modal interface is used in an async context.

## modal.exception.AuthError


```python
class AuthError(modal.exception.Error, modal.exception._GRPCErrorWrapper)
```

Raised when a client has missing or invalid authentication.

```python
__init__(self, message=None)
```


### message

```python
message(self)
```


### status

```python
status(self)
```


### details

```python
details(self)
```

## modal.exception.ClientClosed


```python
class ClientClosed(modal.exception.Error)
```

## modal.exception.ConflictError


```python
class ConflictError(modal.exception.InvalidError, modal.exception._GRPCErrorWrapper)
```

Raised when a resource conflict occurs between the request and current system state.

```python
__init__(self, message=None)
```


### message

```python
message(self)
```


### status

```python
status(self)
```


### details

```python
details(self)
```

## modal.exception.ConnectionError


```python
class ConnectionError(modal.exception.Error)
```

Raised when an issue occurs while connecting to the Modal servers.

## modal.exception.DataLossError


```python
class DataLossError(modal.exception.Error, modal.exception._GRPCErrorWrapper)
```

Raised when data is lost or corrupted.

```python
__init__(self, message=None)
```


### message

```python
message(self)
```


### status

```python
status(self)
```


### details

```python
details(self)
```

## modal.exception.DeprecationError


```python
class DeprecationError(UserWarning)
```

UserWarning category emitted when a deprecated Modal feature or API is used.

## modal.exception.DeserializationError


```python
class DeserializationError(modal.exception.Error)
```

Raised to provide more context when an error is encountered during deserialization.

## modal.exception.Error


```python
class Error(Exception)
```

Base class for all Modal errors. See [`modal.exception`](https://modal.com/docs/sdk/py/latest/modal.exception)
for the specialized error classes.

**Usage**

```python notest
import modal

try:
    ...
except modal.Error:
    # Catch any exception raised by Modal's systems.
    print("Responding to error...")
```

## modal.exception.ExecTimeoutError


```python
class ExecTimeoutError(modal.exception.TimeoutError)
```

Raised when a container process exceeds its execution duration limit and times out.

## modal.exception.ExecutionError


```python
class ExecutionError(modal.exception.Error)
```

Raised when something unexpected happened during runtime.

## modal.exception.FilesystemExecutionError


```python
class FilesystemExecutionError(modal.exception.Error)
```

Raised when an unknown error is thrown during a container filesystem operation.

## modal.exception.FunctionTimeoutError


```python
class FunctionTimeoutError(modal.exception.TimeoutError)
```

Raised when a Function exceeds its execution duration limit and times out.

## modal.exception.InputCancellation


```python
class InputCancellation(BaseException)
```

Raised when the current input is cancelled by the task

Intentionally a BaseException instead of an Exception, so it won't get
caught by unspecified user exception clauses that might be used for retries and
other control flow.

## modal.exception.InteractiveTimeoutError


```python
class InteractiveTimeoutError(modal.exception.TimeoutError)
```

Raised when interactive frontends time out while trying to connect to a container.

## modal.exception.InternalError


```python
class InternalError(modal.exception.Error, modal.exception._GRPCErrorWrapper)
```

Raised when an internal error occurs in the Modal system.

```python
__init__(self, message=None)
```


### message

```python
message(self)
```


### status

```python
status(self)
```


### details

```python
details(self)
```

## modal.exception.InternalFailure


```python
class InternalFailure(modal.exception.Error)
```

Retriable internal error.

## modal.exception.InvalidError


```python
class InvalidError(modal.exception.Error, modal.exception._GRPCErrorWrapper)
```

Raised when user does something invalid.

```python
__init__(self, message=None)
```


### message

```python
message(self)
```


### status

```python
status(self)
```


### details

```python
details(self)
```

## modal.exception.LogsFetchError


```python
class LogsFetchError(modal.exception.Error)
```

Raised when trying to fetch too many logs.

## modal.exception.ModuleNotMountable


```python
class ModuleNotMountable(Exception)
```

## modal.exception.MountUploadTimeoutError


```python
class MountUploadTimeoutError(modal.exception.TimeoutError)
```

Raised when a Mount upload times out.

## modal.exception.NotFoundError


```python
class NotFoundError(modal.exception.Error, modal.exception._GRPCErrorWrapper)
```

Raised when a requested resource was not found.

```python
__init__(self, message=None)
```


### message

```python
message(self)
```


### status

```python
status(self)
```


### details

```python
details(self)
```

## modal.exception.OutputExpiredError


```python
class OutputExpiredError(modal.exception.TimeoutError)
```

Raised when the Output exceeds expiration and times out.

## modal.exception.PermissionDeniedError


```python
class PermissionDeniedError(modal.exception.Error, modal.exception._GRPCErrorWrapper)
```

Raised when a user does not have permission to perform the requested operation.

```python
__init__(self, message=None)
```


### message

```python
message(self)
```


### status

```python
status(self)
```


### details

```python
details(self)
```

## modal.exception.RemoteError


```python
class RemoteError(modal.exception.Error)
```

Raised when an error occurs on the Modal server.

## modal.exception.RequestSizeError


```python
class RequestSizeError(modal.exception.Error)
```

Raised when an operation produces a gRPC request that is rejected by the server for being too large.

## modal.exception.ResourceExhaustedError


```python
class ResourceExhaustedError(modal.exception.Error, modal.exception._GRPCErrorWrapper)
```

Raised when a server-side resource has been exhausted, e.g. a quota or rate limit.

```python
__init__(self, message=None)
```


### message

```python
message(self)
```


### status

```python
status(self)
```


### details

```python
details(self)
```

## modal.exception.SandboxFilesystemDirectoryNotEmptyError


```python
class SandboxFilesystemDirectoryNotEmptyError(modal.exception.SandboxFilesystemError)
```

Raised when a directory is not empty.

## modal.exception.SandboxFilesystemError


```python
class SandboxFilesystemError(modal.exception.Error)
```

Base class for sandbox filesystem errors.

## modal.exception.SandboxFilesystemFileTooLargeError


```python
class SandboxFilesystemFileTooLargeError(modal.exception.SandboxFilesystemError)
```

Raised when a file exceeds the maximum allowed size for a read operation in the sandbox.

## modal.exception.SandboxFilesystemIsADirectoryError


```python
class SandboxFilesystemIsADirectoryError(modal.exception.SandboxFilesystemError)
```

Raised when a file operation in the sandbox targets a directory when it should target a non-directory file.

## modal.exception.SandboxFilesystemNotADirectoryError


```python
class SandboxFilesystemNotADirectoryError(modal.exception.SandboxFilesystemError)
```

Raised when a path component in the sandbox is not a directory.

## modal.exception.SandboxFilesystemNotFoundError


```python
class SandboxFilesystemNotFoundError(modal.exception.SandboxFilesystemError)
```

Raised when a file or directory is not found in the sandbox.

## modal.exception.SandboxFilesystemPathAlreadyExistsError


```python
class SandboxFilesystemPathAlreadyExistsError(modal.exception.SandboxFilesystemError)
```

Raised when a path already exists and the operation requires it to be absent.

## modal.exception.SandboxFilesystemPermissionError


```python
class SandboxFilesystemPermissionError(modal.exception.SandboxFilesystemError)
```

Raised when permission is denied for a file operation in the sandbox.

## modal.exception.SandboxTerminatedError


```python
class SandboxTerminatedError(modal.exception.Error)
```

Raised when a Sandbox is terminated for an internal reason.

## modal.exception.SandboxTimeoutError


```python
class SandboxTimeoutError(modal.exception.TimeoutError)
```

Raised when a Sandbox exceeds its execution duration limit and times out.

## modal.exception.SerializationError


```python
class SerializationError(modal.exception.Error)
```

Raised to provide more context when an error is encountered during serialization.

## modal.exception.ServerWarning


```python
class ServerWarning(UserWarning)
```

Warning originating from the Modal server and re-issued in client code.

## modal.exception.ServiceError


```python
class ServiceError(modal.exception.Error, modal.exception._GRPCErrorWrapper)
```

Raised when an error occurs in basic client/server communication.

```python
__init__(self, message=None)
```


### message

```python
message(self)
```


### status

```python
status(self)
```


### details

```python
details(self)
```

## modal.exception.TimeoutError


```python
class TimeoutError(modal.exception.Error)
```

Base class for Modal timeouts.

## modal.exception.UnimplementedError


```python
class UnimplementedError(modal.exception.Error, modal.exception._GRPCErrorWrapper)
```

Raised when a requested operation is not implemented or not supported.

```python
__init__(self, message=None)
```


### message

```python
message(self)
```


### status

```python
status(self)
```


### details

```python
details(self)
```

## modal.exception.VersionError


```python
class VersionError(modal.exception.Error)
```

Raised when the current client version of Modal is unsupported.

## modal.exception.VolumeUploadTimeoutError


```python
class VolumeUploadTimeoutError(modal.exception.TimeoutError)
```

Raised when a Volume upload times out.

## modal.exception.WorkspaceManagementError


```python
class WorkspaceManagementError(modal.exception.Error)
```

Raised when an error occurs while managing a workspace.

## modal.exception.simulate_preemption

```python
simulate_preemption(wait_seconds, jitter_seconds=0)
```
Utility for simulating a preemption interrupt after `wait_seconds` seconds.
The first interrupt is the SIGINT signal. After 30 seconds, a second
interrupt will trigger.

This second interrupt simulates SIGKILL, and should not be caught.
Optionally add between zero and `jitter_seconds` seconds of additional waiting before first interrupt.

**Usage**

```python notest
import time
from modal.exception import simulate_preemption

simulate_preemption(3)

try:
    time.sleep(4)
except KeyboardInterrupt:
    print("got preempted") # Handle interrupt
    raise
```

See https://modal.com/docs/guide/preemption for more details on preemption
handling.
