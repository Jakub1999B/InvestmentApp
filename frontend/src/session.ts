export function getSessionId(): string {
  const key = "belka-session";
  const existing = localStorage.getItem(key);
  if (existing) {
    return existing;
  }
  const id = crypto.randomUUID();
  localStorage.setItem(key, id);
  return id;
}

export function getStoredApiKey(): string {
  return localStorage.getItem("belka-openai-key") || "";
}

export function setStoredApiKey(value: string) {
  if (value.trim()) {
    localStorage.setItem("belka-openai-key", value.trim());
  } else {
    localStorage.removeItem("belka-openai-key");
  }
}
