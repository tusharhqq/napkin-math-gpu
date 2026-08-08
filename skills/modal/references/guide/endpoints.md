# Endpoints

Deploy a production-ready LLM inference endpoint on Modal's managed
infrastructure with a single command:

```bash
modal endpoint create --model Qwen/Qwen3.5-4B
```

Endpoints support both open model weights and your own custom fine tunes,
sourced from either a Hugging Face repo or a Modal Volume.

They provide a number of built-in features:

* **Fast inference by default** — every endpoint runs behind a low-latency
  request proxy on tuned open-source inference engines, with SOTA speculative
  decoding wherever the recipe supports it.
* **Usage-based pricing** — you pay only for the *compute* your endpoint uses,
  so you reap the benefits of our compute engine optimizations.
* **Scale-to-zero autoscaling** — endpoints scale up under load and down to zero
  when idle, with no manual tuning required.

This page is a high-level guide to Modal Endpoints.

## Getting started

Modal supports deploying pre-trained open and custom weight models from the
following families:

* Qwen
* Kimi
* Gemma4
* DeepSeek
* Nemotron
* GPT-OSS
* GLM

Browse the full catalog on the [**Endpoints**](https://modal.com/endpoints) tab
in the dashboard.

Spin up an endpoint for `Qwen/Qwen3.5-4B`:

```bash
modal endpoint create --model Qwen/Qwen3.5-4B
```

Modal resolves the model, selects a compatible recipe, and starts provisioning.
The command prints the endpoint ID and a dashboard link where you can watch it
come online. You can also create endpoints from the
[**Endpoints**](https://modal.com/endpoints) tab in the dashboard — the form
collects the same options.

If you omit the `name` argument, Modal derives one from the model
(`Qwen/Qwen3.5-4B` → `qwen3-5-4b`).

## Proxy tokens

Endpoints are authenticated by default. To create and call an authenticated
endpoint, you need a [proxy token](/docs/guide/webhook-proxy-auth) pair.
The token is passed on every request as the `Modal-Key` and `Modal-Secret` headers.

Create a proxy token with the CLI:

```bash
modal workspace proxy-tokens create
```

This prints the token ID and secret. The secret is only shown at creation time
and can't be retrieved later, so store it somewhere safe:

```
Modal-Key: wk-...
Modal-Secret: ws-...
```

If your workspace has [RBAC](/docs/guide/rbac) enabled, you'll also need to explicitly
associate the new token with the environment where you'll create the endpoint:

```bash
modal workspace proxy-tokens allow wk-... main
```

You can also make requests to an authenticated endpoint using the
[`modal curl`](/docs/cli/latest/curl) utility. This performs transparent
authentication using your Modal API credentials, although API authentication
adds some latency so it is best suited for basic testing and demonstrations.

To create an endpoint that accepts unauthenticated requests instead, pass
`--unauthenticated`.

## Calling your endpoint

Once the endpoint is live, it serves the OpenAI Chat Completions API at the
endpoint URL — find it in the dashboard or with `modal endpoint list`. The API
is served under `/v1`, and the model name to pass is the base model repo ID (for
catalog and Volume models) or your custom Hugging Face repo ID.

List the models the endpoint serves with a `GET` request, passing your
[proxy token](#proxy-tokens) in the `Modal-Key` and `Modal-Secret` headers:

```bash
curl "<your-endpoint-url>/v1/models" \
  -H "Modal-Key: $MODAL_PROXY_TOKEN_ID" \
  -H "Modal-Secret: $MODAL_PROXY_TOKEN_SECRET"
```

## Serving custom weights

Point an endpoint at a fine-tuned checkpoint instead of a catalog model. A
custom model is always served against a base model from the catalog: pass that
base model with `--model` so Modal can pick a compatible recipe, then point at
your weights with the `--custom-hf-*` or `--custom-volume-*` flags.

From a Hugging Face repo (use `--custom-hf-token` for gated or private repos):

```bash
modal endpoint create \
  --name my-ft \
  --model Qwen/Qwen3.6-27B \
  --custom-hf-repo aisingapore/Qwen-SEA-LION-v4.5-27B-IT \
  --custom-hf-revision da42f2c0984d716fb2032e4176d81adfac98c630
```

From a Modal Volume (the model directory must contain `config.json`):

```bash
modal endpoint create \
  --name my-volume-ft \
  --model Qwen/Qwen3.5-4B \
  --custom-volume-name my-volume \
  --custom-volume-path /checkpoints/1234
```

## Choosing where it runs

Two placement controls:

* **Routing region** (`--routing-region`) — where the request proxy is anchored.
  Pick the region closest to your callers: `us-west` (default), `us-east`,
  `ca-central`, `eu-west`, or `ap-south`.
* **Compute placement** (`--compute-region`, `--colocate-compute`) — by default,
  Modal places containers by availability. Pass `--compute-region` to select
  where containers run independently from request routing. You can repeat the
  option to allow scheduling in multiple regions. Alternatively, pass
  `--colocate-compute` to use the routing region.

Select compute regions independently from request routing:

```bash
modal endpoint create \
  --model Qwen/Qwen3.5-4B \
  --routing-region us-east \
  --compute-region us-west
```

Or run compute in the routing region:

```bash
modal endpoint create \
  --model Qwen/Qwen3.5-4B \
  --routing-region us-east \
  --colocate-compute
```

Selecting compute regions with `--compute-region` or `--colocate-compute`
incurs a [region selection multiplier](/docs/guide/region-selection#pricing).

## Managing endpoints

You can list all endpoints in an environment and their current status.

```bash
modal endpoint list --env prod
modal endpoint list --env prod --json  # Contains more details
```

Stop an endpoint when you no longer need it. This tears down its serving
containers and stops billing.

```bash
modal endpoint stop qwen3-5-4b --env prod
```

## Viewing the source

Modal Endpoints are built with the Modal SDK and leverage our new
high-performance [Server](/docs/guide/servers) primitive. You can see the
underlying code by navigating to the "Source" panel in the endpoint dashboard.

## Pricing

Endpoints bill for the GPU and CPU their containers use while running, at
standard Modal compute rates. Because endpoints scale to zero by default, you
pay nothing for compute while idle. You can adjust the autoscaling configuration
overrides in the UI. Region pinning applies a
[region selection multiplier](https://modal.com/pricing).
