import { GPU_PROFILES, type Dtype, type GpuProfile } from "../data/profiles";

type ExecutionMode = "serial" | "overlapped";

interface Inputs {
  profileId: GpuProfile["id"];
  dtype: Dtype;
  flops: number;
  deviceBytes: number;
  h2dBytes: number;
  d2hBytes: number;
  g2gBytes: number;
  launches: number;
  weightsGb: number;
  activationsGb: number;
  kvGb: number;
  workspaceGb: number;
  mode: ExecutionMode;
}

interface Estimate {
  computeMs: number;
  memoryMs: number;
  transferMs: number;
  g2gMs: number;
  launchMs: number;
  totalMs: number;
  bottleneck: "compute" | "HBM" | "PCIe" | "inter-GPU" | "launch";
  capacityGb: number;
  headroomGb: number;
}

const $ = <T extends Element>(selector: string): T => {
  const node = document.querySelector<T>(selector);
  if (!node) throw new Error(`Missing required element: ${selector}`);
  return node;
};

const $$ = <T extends Element>(selector: string): T[] =>
  Array.from(document.querySelectorAll<T>(selector));

const getNumber = (name: keyof Inputs): number => {
  const input = $<HTMLInputElement>(`[data-input="${name}"]`);
  const value = Number(input.value);
  return Number.isFinite(value) && value >= 0 ? value : 0;
};

const getProfile = (id: GpuProfile["id"]): GpuProfile =>
  GPU_PROFILES.find((profile) => profile.id === id) ?? GPU_PROFILES[0];

const selectedProfileId = (): GpuProfile["id"] =>
  ($<HTMLElement>(".profile-option.selected").dataset.profile ?? "h100") as GpuProfile["id"];

const selectedMode = (): ExecutionMode =>
  ($<HTMLInputElement>('input[name="execution"]:checked').value ?? "overlapped") as ExecutionMode;

const readInputs = (): Inputs => ({
  profileId: selectedProfileId(),
  dtype: $<HTMLSelectElement>('[data-input="dtype"]').value as Dtype,
  flops: getNumber("flops"),
  deviceBytes: getNumber("deviceBytes"),
  h2dBytes: getNumber("h2dBytes"),
  d2hBytes: getNumber("d2hBytes"),
  g2gBytes: getNumber("g2gBytes"),
  launches: getNumber("launches"),
  weightsGb: getNumber("weightsGb"),
  activationsGb: getNumber("activationsGb"),
  kvGb: getNumber("kvGb"),
  workspaceGb: getNumber("workspaceGb"),
  mode: selectedMode(),
});

const computeEstimate = (inputs: Inputs): Estimate => {
  const profile = getProfile(inputs.profileId);
  const computeTflops = profile.computeTflops[inputs.dtype] ?? profile.computeTflops.bf16 ?? 0;
  const computeMs = computeTflops > 0 ? (inputs.flops / (computeTflops * 1e12)) * 1e3 : 0;
  const memoryMs = profile.hbmGbps > 0 ? (inputs.deviceBytes / (profile.hbmGbps * 1e9)) * 1e3 : 0;
  const h2dMs = profile.h2dGbps ? (inputs.h2dBytes / (profile.h2dGbps * 1e9)) * 1e3 : 0;
  const d2hMs = profile.d2hGbps ? (inputs.d2hBytes / (profile.d2hGbps * 1e9)) * 1e3 : 0;
  const transferMs = h2dMs + d2hMs;
  const g2gMs = profile.g2gGbps > 0 ? (inputs.g2gBytes / (profile.g2gGbps * 1e9)) * 1e3 : 0;
  const launchMs = profile.launchUs ? (inputs.launches * profile.launchUs) / 1e3 : 0;
  const resourceFloors = {
    compute: computeMs,
    HBM: memoryMs,
    PCIe: transferMs,
    "inter-GPU": g2gMs,
    launch: launchMs,
  } as const;
  const bottleneck = (Object.entries(resourceFloors).sort((a, b) => b[1] - a[1])[0]?.[0] ??
    "compute") as Estimate["bottleneck"];
  const totalMs =
    inputs.mode === "serial"
      ? Math.max(computeMs, memoryMs) + transferMs + g2gMs + launchMs
      : Math.max(computeMs, memoryMs, transferMs, g2gMs, launchMs);
  const capacityGb = inputs.weightsGb + inputs.activationsGb + inputs.kvGb + inputs.workspaceGb;

  return {
    computeMs,
    memoryMs,
    transferMs,
    g2gMs,
    launchMs,
    totalMs,
    bottleneck,
    capacityGb,
    headroomGb: profile.capacityGb - capacityGb,
  };
};

const formatMs = (value: number): string => {
  if (!Number.isFinite(value)) return "—";
  if (value < 0.01) return `${value.toFixed(3)} ms`;
  if (value < 10) return `${value.toFixed(1)} ms`;
  return `${Math.round(value)} ms`;
};

const formatSeconds = (ms: number): string => (ms / 1e3).toFixed(3);
const scientific = (value: number, digits = 2): string => value.toExponential(digits);

const setText = (selector: string, value: string): void => {
  $(selector).textContent = value;
};

const updateProfileSummary = (profile: GpuProfile, dtype: Dtype): void => {
  const compute = profile.computeTflops[dtype] ?? profile.computeTflops.bf16;
  setText("[data-profile-short]", `(${profile.id.toUpperCase()})`);
  setText("[data-profile-compute]", compute ? `${compute.toFixed(0)} TFLOP/s` : "not published");
  setText("[data-profile-hbm]", `${(profile.hbmGbps / 1000).toFixed(1)} TB/s`);
  setText("[data-profile-capacity]", `${profile.capacityGb} GB`);
  setText("[data-profile-pcie]", profile.h2dGbps ? `${profile.h2dGbps.toFixed(0)} GB/s` : "not profiled");
  setText("[data-profile-g2g]", `${profile.g2gGbps.toFixed(0)} GB/s`);
  setText("[data-profile-launch]", profile.launchUs ? `${profile.launchUs.toFixed(1)} μs` : "not profiled");
  setText("[data-profile-source]", `Source: ${profile.source}`);
  setText("[data-profile-captured]", `${profile.status === "calibrated" ? "Captured" : "Status"}: ${profile.captured}`);
  setText("[data-profile-hbm]", `${(profile.hbmGbps / 1000).toFixed(1)} TB/s`);
  setText("[data-footer-profile]", `Provider: ${profile.status === "calibrated" ? "Modal" : "NVIDIA"}\nProfile: ${profile.label}\nMeasured: ${profile.captured}\nMethod: ${profile.status === "calibrated" ? "microbench + roofline" : "vendor ceiling planning"}`);
};

const updateResourceBar = (resource: string, value: number, maxValue: number): void => {
  const row = $<HTMLElement>(`[data-resource="${resource}"]`);
  const bar = $<HTMLElement>(`[data-resource="${resource}"] i`);
  const output = $<HTMLOutputElement>(`[data-resource="${resource}"] output`);
  const percent = maxValue > 0 ? Math.max(1.5, (value / maxValue) * 100) : 0;
  bar.style.width = `${Math.min(100, percent)}%`;
  output.textContent = formatMs(value);
  row.setAttribute("aria-label", `${resource} floor ${formatMs(value)}`);
};

const render = (track = false): Estimate => {
  const inputs = readInputs();
  const profile = getProfile(inputs.profileId);
  const estimate = computeEstimate(inputs);
  const computeTflops = profile.computeTflops[inputs.dtype] ?? profile.computeTflops.bf16 ?? 0;

  updateProfileSummary(profile, inputs.dtype);
  setText('[data-output="compute"]', formatSeconds(estimate.computeMs));
  setText('[data-output="hbmBandwidth"]', scientific(profile.hbmGbps * 1e9));
  setText('[data-output="memory"]', formatSeconds(estimate.memoryMs));
  setText('[data-output="transfer"]', formatSeconds(estimate.transferMs));
  setText('[data-output="g2g"]', formatSeconds(estimate.g2gMs));
  setText('[data-output="launch"]', formatSeconds(estimate.launchMs));
  setText("[data-transfer-note]", profile.h2dGbps ? "two directions" : "not profiled; omitted");
  setText("[data-launch-note]", profile.launchUs ? "from profile" : "not profiled; omitted");
  setText("[data-result-mode]", `(${inputs.mode})`);
  setText("[data-bottleneck]", `${estimate.bottleneck}-bound`);
  setText("[data-total-ms]", formatMs(estimate.totalMs));
  setText("[data-result-explanation]", `Your time-floor estimate is ${estimate.bottleneck}-bound.${estimate.headroomGb < 0 ? " The capacity check also fails." : ""}`);

  const maxFloor = Math.max(
    estimate.computeMs,
    estimate.memoryMs,
    estimate.transferMs,
    estimate.g2gMs,
    estimate.launchMs,
  );
  updateResourceBar("compute", estimate.computeMs, maxFloor);
  updateResourceBar("memory", estimate.memoryMs, maxFloor);
  updateResourceBar("transfer", estimate.transferMs, maxFloor);
  updateResourceBar("g2g", estimate.g2gMs, maxFloor);
  updateResourceBar("launch", estimate.launchMs, maxFloor);

  setText("[data-capacity-usage]", `${estimate.capacityGb.toFixed(0)} GB`);
  setText("[data-capacity-limit]", `${profile.capacityGb} GB`);
  setText("[data-capacity-headroom]", `${estimate.headroomGb < 0 ? "−" : "+"}${Math.abs(estimate.headroomGb).toFixed(0)} GB`);
  setText('[data-capacity-row="weights"]', `${inputs.weightsGb.toFixed(0)} GB`);
  setText('[data-capacity-row="activations"]', `${inputs.activationsGb.toFixed(0)} GB`);
  setText('[data-capacity-row="other"]', `${(inputs.kvGb + inputs.workspaceGb).toFixed(0)} GB`);

  const status = $<HTMLElement>("[data-capacity-status]");
  status.textContent = estimate.headroomGb >= 0 ? "Fits" : "Does not fit";
  status.classList.toggle("status-ok", estimate.headroomGb >= 0);
  status.classList.toggle("status-danger", estimate.headroomGb < 0);
  setText(
    "[data-capacity-warning]",
    estimate.headroomGb >= 0
      ? `${estimate.headroomGb.toFixed(0)} GB of HBM headroom remains for runtime state and fragmentation.`
      : `Exceeds HBM by ${Math.abs(estimate.headroomGb).toFixed(0)} GB. Reduce batch, sequence length, or precision—or shard the workload.`,
  );

  setText(
    "[data-equation-output]",
    `T_comp   = ${scientific(inputs.flops)} / ${scientific(computeTflops * 1e12)} = ${formatSeconds(estimate.computeMs)} s\n` +
      `T_hbm    = ${scientific(inputs.deviceBytes)} / ${scientific(profile.hbmGbps * 1e9)} = ${formatSeconds(estimate.memoryMs)} s\n` +
      `T_pcie   = ${formatSeconds(estimate.transferMs)} s${profile.h2dGbps ? "" : " (not profiled)"}\n` +
      `T_g2g    = ${formatSeconds(estimate.g2gMs)} s\n` +
      `T_launch = ${inputs.launches.toFixed(0)} × ${profile.launchUs ? `${profile.launchUs.toFixed(2)}e-6` : "—"} = ${formatSeconds(estimate.launchMs)} s`,
  );
  const operator = inputs.mode === "serial" ? "max(T_comp, T_hbm) + T_pcie + T_g2g + T_launch" : "max(T_comp, T_hbm, T_pcie, T_g2g, T_launch)";
  setText("[data-equation-total]", `T_est = ${operator} = ${formatSeconds(estimate.totalMs)} s`);
  setText("[data-equation-bottleneck]", `Bottleneck = ${estimate.bottleneck}`);
  setText("[data-scenario-name]", `custom workload · ${inputs.dtype.toUpperCase()}`);

  if (track) {
    window.posthog?.capture("gpu_estimate_run", {
      gpu_profile: profile.id,
      dtype: inputs.dtype,
      execution_model: inputs.mode,
      bottleneck: estimate.bottleneck,
      capacity_fits: estimate.headroomGb >= 0,
    });
  }
  return estimate;
};

const writeInput = (name: keyof Inputs, value: string | number): void => {
  const input = $<HTMLInputElement | HTMLSelectElement>(`[data-input="${name}"]`);
  input.value = String(value);
};

const selectProfile = (profileId: GpuProfile["id"], track = false): void => {
  const profile = getProfile(profileId);
  $$(".profile-option").forEach((node) => {
    const selected = (node as HTMLElement).dataset.profile === profileId;
    node.classList.toggle("selected", selected);
    node.setAttribute("aria-checked", selected ? "true" : "false");
  });
  const dtypeSelect = $<HTMLSelectElement>('[data-input="dtype"]');
  Array.from(dtypeSelect.options).forEach((option) => {
    option.disabled = profile.computeTflops[option.value as Dtype] == null;
  });
  if (profile.computeTflops[dtypeSelect.value as Dtype] == null) dtypeSelect.value = "bf16";
  render();
  if (track) window.posthog?.capture("gpu_profile_selected", { gpu_profile: profileId, status: profile.status });
};

const loadExample = (): void => {
  selectProfile("h100");
  writeInput("dtype", "bf16");
  writeInput("flops", 2e13);
  writeInput("deviceBytes", 1.86e11);
  writeInput("h2dBytes", 1e8);
  writeInput("d2hBytes", 1e8);
  writeInput("g2gBytes", 1e9);
  writeInput("launches", 1000);
  writeInput("weightsGb", 96);
  writeInput("activationsGb", 72);
  writeInput("kvGb", 12);
  writeInput("workspaceGb", 6);
  $<HTMLInputElement>('input[name="execution"][value="overlapped"]').checked = true;
  setText("[data-scenario-name]", "LLM prefill · BF16");
  render();
  window.posthog?.capture("gpu_example_loaded", { example: "llm_prefill_bf16" });
};

const scenarioPayload = (): Record<string, unknown> => {
  const inputs = readInputs();
  const estimate = computeEstimate(inputs);
  return {
    schema_version: 1,
    generated_at: new Date().toISOString(),
    inputs,
    estimate,
    disclaimer: "Lower-bound napkin estimate; not a latency promise.",
  };
};

const exportJson = (): void => {
  const blob = new Blob([JSON.stringify(scenarioPayload(), null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "gpu-napkin-estimate.json";
  anchor.click();
  URL.revokeObjectURL(url);
  window.posthog?.capture("gpu_estimate_exported", { format: "json" });
};

const copyShareLink = async (): Promise<void> => {
  const inputs = readInputs();
  const url = new URL(window.location.href);
  Object.entries(inputs).forEach(([key, value]) => url.searchParams.set(key, String(value)));
  await navigator.clipboard.writeText(url.toString());
  const button = $<HTMLButtonElement>("[data-copy-link]");
  const original = button.textContent;
  button.textContent = "Copied";
  window.setTimeout(() => (button.textContent = original), 1400);
  window.posthog?.capture("gpu_share_link_copied", { gpu_profile: inputs.profileId });
};

const loadFromQuery = (): void => {
  const query = new URLSearchParams(window.location.search);
  const profileId = query.get("profileId") as GpuProfile["id"] | null;
  if (profileId && GPU_PROFILES.some((profile) => profile.id === profileId)) selectProfile(profileId);
  const numericKeys: Array<keyof Inputs> = [
    "flops",
    "deviceBytes",
    "h2dBytes",
    "d2hBytes",
    "g2gBytes",
    "launches",
    "weightsGb",
    "activationsGb",
    "kvGb",
    "workspaceGb",
  ];
  numericKeys.forEach((key) => {
    const value = query.get(key);
    if (value != null && Number.isFinite(Number(value))) writeInput(key, value);
  });
  const dtype = query.get("dtype") as Dtype | null;
  if (dtype) writeInput("dtype", dtype);
  const mode = query.get("mode") as ExecutionMode | null;
  if (mode) {
    const radio = document.querySelector<HTMLInputElement>(`input[name="execution"][value="${mode}"]`);
    if (radio) radio.checked = true;
  }
};

$$<HTMLButtonElement>(".profile-option").forEach((button) => {
  button.addEventListener("click", () => selectProfile(button.dataset.profile as GpuProfile["id"], true));
});

$$<HTMLInputElement | HTMLSelectElement>("[data-input]").forEach((input) => {
  input.addEventListener("input", () => render());
});

$$<HTMLInputElement>('input[name="execution"]').forEach((radio) => {
  radio.addEventListener("change", () => {
    $$(".execution-model label").forEach((label) => label.classList.remove("selected"));
    radio.closest("label")?.classList.add("selected");
    render();
  });
});

$$<HTMLButtonElement>("[data-run-estimate]").forEach((button) =>
  button.addEventListener("click", () => {
    render(true);
    $(".result-panel").scrollIntoView({ behavior: "smooth", block: "nearest" });
  }),
);

$<HTMLButtonElement>("[data-load-example]").addEventListener("click", loadExample);
$<HTMLButtonElement>("[data-export-json]").addEventListener("click", exportJson);
$<HTMLButtonElement>("[data-copy-link]").addEventListener("click", () => void copyShareLink());

loadFromQuery();
selectProfile(selectedProfileId());
render();
