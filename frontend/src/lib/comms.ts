/** Communications types (mirror backend schemas). */

export interface Person {
  id: string;
  display_name: string;
  department: string | null;
}

export interface Conversation {
  id: string;
  kind: "direct" | "channel" | "announcements";
  title: string;
  members: Person[];
  unread: number;
  last_message_at: string | null;
}

export interface Message {
  id: string;
  sender: Person;
  body: string;
  requires_ack: boolean;
  ai_generated: boolean;
  created_at: string;
  acknowledged_by_me: boolean;
  ack_count: number;
}

export interface Task {
  id: string;
  title: string;
  description: string | null;
  assigned_to: Person;
  assigned_by: Person;
  due_at: string | null;
  priority: "low" | "normal" | "high" | "urgent";
  status: "open" | "in_progress" | "blocked" | "done" | "cancelled";
  acknowledged_at: string | null;
  completed_at: string | null;
  overdue: boolean;
  ai_generated: boolean;
  updates: Array<{ author: Person; status: string | null; note: string; created_at: string }>;
}

export interface ReportRequest {
  id: string;
  requested_by: Person;
  requested_from: Person;
  topic: string;
  due_at: string | null;
  status: "open" | "submitted" | "cancelled";
}

export interface Report {
  id: string;
  author: Person;
  kind: "morning_plan" | "end_of_day" | "requested";
  report_date: string;
  body: string;
  created_at: string;
}

export interface TeamRow {
  user: Person;
  open_tasks: number;
  overdue_tasks: number;
  done_last_7_days: number;
  morning_plan_today: boolean;
  end_of_day_yesterday: boolean;
}

export const PRIORITY_TONE = {
  low: "neutral",
  normal: "neutral",
  high: "warning",
  urgent: "danger",
} as const;
