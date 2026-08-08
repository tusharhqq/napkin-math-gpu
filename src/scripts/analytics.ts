import posthog from "posthog-js";

declare global {
  interface Window {
    posthog?: typeof posthog;
  }
}

const apiKey = import.meta.env.PUBLIC_POSTHOG_KEY;
const apiHost = import.meta.env.PUBLIC_POSTHOG_HOST;

if (apiKey && apiHost) {
  posthog.init(apiKey, {
    api_host: apiHost,
    autocapture: true,
    capture_pageview: true,
    capture_pageleave: true,
    disable_session_recording: false,
    person_profiles: "identified_only",
    session_recording: {
      maskAllInputs: true,
    },
  });
  window.posthog = posthog;
}
