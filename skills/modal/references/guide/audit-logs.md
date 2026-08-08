# Audit Logs

<Callout variant="gated-feature">
Audit logs are available on the <a href="/pricing" target="_blank" rel="noopener">Enterprise plan</a>. Contact <a href="mailto:sales@modal.com">sales@modal.com</a> for more information.
</Callout>

Audit logs give your workspace an append-only record of the sensitive
actions that change its state — who did what, when, to which resource, and
from where. They are designed for compliance reviews, incident
investigation, and answering questions like *"did anyone delete this Secret
last Thursday?"* without asking Modal support.

Audit logs are viewable within the <a href="/settings/audit-logs" target="_blank" rel="noopener" class="text-c-green-100 hover:underline">settings page</a>.

<center>
<video controls autoplay muted playsinline>
<source src="https://modal-public-assets.s3.us-east-1.amazonaws.com/docs/audit-logs-v2-demo-2.mp4" type="video/mp4">
</video>
</center>

## Fields

Every audit event captures the same shape alongside the time it occurred:

| Field                 | What it is                                                                                                                         |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `action`              | The kind of change that happened — e.g. `secret.create`, `app.deploy`. See the full list [below](#actions).                        |
| `actor`               | The user or service user that initiated the action.                                                                                |
| `targets`             | The resource(s) the action affected, each recorded by ID so the event stays attributable after a rename or delete.                 |
| `context.environment` | The environment the action was scoped to.                                                                                          |
| `context.ip_address`  | The client IP address.                                                                                                             |
| `context.source`      | `web` for the dashboard, `sdk` for the Modal CLI and client libraries.                                                             |
| `status`              | Whether the action succeeded or failed.                                                                                            |
| `metadata`            | Action-specific extra fields — e.g. the old and new budget values for `workspace.set_budget`, or the requested region for a Proxy. |

## Filtering

Filters are entered in the search bar above the table as `key:value`
pairs, separated by spaces. Any filter can be **negated** by prefixing it
with `-` to exclude matching events. The search bar autocompletes keys
and values as you type.

For example:

| Filter                                       | Matches                                          |
| -------------------------------------------- | ------------------------------------------------ |
| `action:secret.create`                       | Every Secret created in the selected time range. |
| `-status:success`                            | All actions that did not succeed.                |
| `action:volume.delete` `-actor_type:service` | Volume deletions by non-service users.           |

## Actions

The table below lists every action currently recorded. New actions will be
added as additional workspace operations are instrumented.

> Note: **container runtime activity is not audited.** Audit logs record
> workspace-level actions (deploying an App, creating a Volume, revoking a
> token) — not individual Function invocations or Sandbox `exec` calls,
> which are captured in Function and Sandbox logs.

<br />

<!-- AUDIT_LOG_V2_ACTIONS_START: generated from ACTION_DESCRIPTIONS, do not edit by hand -->

| Action                               | Description                                                                                                                                                                                                                                                         |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `access_grant.approve`               | A workspace manager approved a pending Modal-admin access grant.                                                                                                                                                                                                    |
| `access_grant.revoke`                | A workspace manager revoked an active Modal-admin access grant.                                                                                                                                                                                                     |
| `app.deploy`                         | An App was deployed to the workspace (via `modal deploy` or implicitly via `App.lookup`).                                                                                                                                                                           |
| `app.rollback`                       | An App was rolled back to an earlier deployed version.                                                                                                                                                                                                              |
| `app.rollover`                       | An App was rolled over — its current version was redeployed, restarting running tasks.                                                                                                                                                                              |
| `app.run`                            | An ephemeral App was started with `modal run` or `modal serve`.                                                                                                                                                                                                     |
| `app.stop`                           | An App was stopped from the dashboard or with `modal app stop`.                                                                                                                                                                                                     |
| `container.stop`                     | A running container (task) was terminated from the dashboard or CLI. Routine container exits at the end of a call are not audited.                                                                                                                                  |
| `dict.create`                        | A Dict was created.                                                                                                                                                                                                                                                 |
| `dict.get`                           | An existing Dict was looked up by name or by ID.                                                                                                                                                                                                                    |
| `domain.create`                      | A custom domain was attached to an environment.                                                                                                                                                                                                                     |
| `domain.delete`                      | A custom domain was removed.                                                                                                                                                                                                                                        |
| `environment.create`                 | A new environment was created in the workspace.                                                                                                                                                                                                                     |
| `environment.delete`                 | An environment was deleted.                                                                                                                                                                                                                                         |
| `environment.get`                    | An environment was looked up by name.                                                                                                                                                                                                                               |
| `environment.set_budget`             | An environment's spend budget was updated or cleared. The previous and new per-cycle budget values, effective maximum budget, and whether the budget changed are recorded in event metadata.                                                                        |
| `environment.set_managed`            | An environment was toggled between managed and unmanaged. Disabling managed access removes every per-environment role for that environment; whether it's now managed is recorded in the event metadata.                                                             |
| `environment.update`                 | An environment's settings changed — name, web suffix, or per-environment concurrency limits. Before/after values are recorded in the event metadata.                                                                                                                |
| `environment.update_member`          | A user or service user's per-environment role (Contributor / Viewer) was changed, or their environment-level access was removed. Independent of their workspace-level role.                                                                                         |
| `image.delete`                       | An Image was deleted.                                                                                                                                                                                                                                               |
| `invite.create_for_workspace`        | A workspace-wide invite link was generated by a workspace admin.                                                                                                                                                                                                    |
| `member.delete`                      | A member was removed from the workspace.                                                                                                                                                                                                                            |
| `member.set_role`                    | A workspace member's workspace-wide role (Owner / Manager / User) was changed. The affected member(s) appear in the event targets and the new role(s) are recorded in the event metadata. Per-environment access is set separately via `environment.update_member`. |
| `nfs.create`                         | A NetworkFileSystem was created.                                                                                                                                                                                                                                    |
| `nfs.get`                            | An existing NetworkFileSystem was looked up by name.                                                                                                                                                                                                                |
| `proxy.add_ip`                       | A static egress IP was added to a Proxy.                                                                                                                                                                                                                            |
| `proxy.create`                       | A Proxy was created. The requested name and region are recorded in the event metadata.                                                                                                                                                                              |
| `proxy.delete`                       | A Proxy was deleted.                                                                                                                                                                                                                                                |
| `queue.delete`                       | A Queue was deleted.                                                                                                                                                                                                                                                |
| `queue.get`                          | An existing Queue was looked up by ID.                                                                                                                                                                                                                              |
| `sandbox.create`                     | A Sandbox was launched.                                                                                                                                                                                                                                             |
| `sandbox.terminate`                  | A Sandbox was explicitly terminated before its natural exit.                                                                                                                                                                                                        |
| `secret.create`                      | A Secret was created or its values were overwritten (via `modal secret create` or the dashboard).                                                                                                                                                                   |
| `secret.get`                         | A named Secret was resolved to an ID (e.g. at deploy, or when opening a secret in the dashboard). Values are not returned; only the Secret's ID and metadata are.                                                                                                   |
| `token.delete`                       | An API token was revoked.                                                                                                                                                                                                                                           |
| `user.create`                        | A new user account was created.                                                                                                                                                                                                                                     |
| `volume.create`                      | A Volume was created.                                                                                                                                                                                                                                               |
| `volume.delete`                      | A Volume was deleted.                                                                                                                                                                                                                                               |
| `volume.get`                         | An existing Volume was looked up by name or by ID.                                                                                                                                                                                                                  |
| `volume.rename`                      | A Volume was renamed.                                                                                                                                                                                                                                               |
| `workspace.create`                   | A new workspace was created.                                                                                                                                                                                                                                        |
| `workspace.downgrade`                | A workspace was downgraded to a lower billing plan.                                                                                                                                                                                                                 |
| `workspace.join`                     | A user joined a workspace (by accepting an invite or self-serve signup).                                                                                                                                                                                            |
| `workspace.leave`                    | A user left a workspace.                                                                                                                                                                                                                                            |
| `workspace.set_budget`               | A workspace's spend budget was updated. The previous and new per-cycle budget values are recorded in the event metadata.                                                                                                                                            |
| `workspace.update_github_autojoin`   | Whether members of the linked GitHub organization can join the workspace without an invite was changed.                                                                                                                                                             |
| `workspace.update_identity_provider` | A workspace's identity provider (Okta) configuration was changed. Enabling SSO enforcement immediately logs out any non-Okta sessions.                                                                                                                              |

<!-- AUDIT_LOG_V2_ACTIONS_END -->
