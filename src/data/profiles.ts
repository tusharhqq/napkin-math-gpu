export type Dtype = "bf16" | "fp16" | "fp8" | "tf32" | "fp32";

export interface GpuProfile {
  id: "h100" | "b200" | "b300";
  label: string;
  subtitle: string;
  status: "calibrated" | "planning";
  source: string;
  captured: string;
  capacityGb: number;
  computeTflops: Partial<Record<Dtype, number>>;
  hbmGbps: number;
  h2dGbps: number | null;
  d2hGbps: number | null;
  g2gGbps: number;
  launchUs: number | null;
  sms: number | null;
}

export const GPU_PROFILES: GpuProfile[] = [
  {
    id: "h100",
    label: "H100 SXM 80GB",
    subtitle: "NVIDIA Hopper",
    status: "calibrated",
    source: "Modal full profile",
    captured: "2026-08-08",
    capacityGb: 80,
    computeTflops: {
      bf16: 717.3949,
      fp16: 693.4609,
      tf32: 344.889,
      fp32: 66.0,
    },
    hbmGbps: 2999.672,
    h2dGbps: 55.4504,
    d2hGbps: 55.4762,
    g2gGbps: 392.9822,
    launchUs: 4.6586,
    sms: 132,
  },
  {
    id: "b200",
    label: "B200 SXM 180GB",
    subtitle: "NVIDIA Blackwell",
    status: "planning",
    source: "NVIDIA vendor ceilings",
    captured: "not calibrated",
    capacityGb: 180,
    computeTflops: {
      bf16: 2250,
      fp16: 2250,
      fp8: 4500,
      tf32: 1125,
      fp32: 75,
    },
    hbmGbps: 8000,
    h2dGbps: null,
    d2hGbps: null,
    g2gGbps: 1800,
    launchUs: null,
    sms: null,
  },
  {
    id: "b300",
    label: "B300 SXM 288GB",
    subtitle: "NVIDIA Blackwell Ultra",
    status: "planning",
    source: "NVIDIA vendor ceilings",
    captured: "not calibrated",
    capacityGb: 288,
    computeTflops: {
      bf16: 2250,
      fp16: 2250,
      fp8: 4500,
      tf32: 1125,
      fp32: 75,
    },
    hbmGbps: 8000,
    h2dGbps: null,
    d2hGbps: null,
    g2gGbps: 1800,
    launchUs: null,
    sms: null,
  },
];
