export interface Account {
  id: number;
  label: string;
  phone: string;
  status: string;
  active: boolean;
  has_session: boolean;
  created_at: string;
}

export interface Prompt {
  id: number;
  name: string;
  version: number;
  system_text: string;
  active: boolean;
  created_at: string;
}

export interface Group {
  id: number;
  telegram_id: number;
  title: string;
  account_id: number | null;
  prompt_id: number | null;
  mode: "mention" | "always" | "off";
  active: boolean;
  created_at: string;
}

export interface Message {
  id: number;
  group_id: number;
  sender_name: string;
  direction: "in" | "out";
  text: string;
  created_at: string;
}

export interface Decision {
  id: number;
  group_id: number;
  action: string;
  reply_text: string;
  reason: string;
  created_at: string;
}

export interface Event {
  id: number;
  level: string;
  source: string;
  message: string;
  created_at: string;
}

export interface Settings {
  app_name: string;
  telegram_api_id: number;
  telegram_api_configured: boolean;
  gemini_configured: boolean;
  gemini_model: string;
  max_context_messages: number;
  max_replies_per_hour: number;
  max_replies_per_day: number;
}
