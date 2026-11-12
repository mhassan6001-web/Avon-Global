/** Real-time event model (pure). Events carry ids only; screens re-fetch details. */

export interface RealtimeEvent {
  type: string;
  conversation_id?: string;
  message_id?: string;
  task_id?: string;
  request_id?: string;
  status?: string;
  requires_ack?: boolean;
}

export interface Notice {
  id: string;
  text: string;
  href: string;
  at: number;
}

/** Turn an event into a human notice, or null for events that need none. */
export function toNotice(event: RealtimeEvent, at = Date.now()): Notice | null {
  const id = `${event.type}:${event.message_id ?? event.task_id ?? event.request_id ?? at}`;
  switch (event.type) {
    case "message.created":
      return {
        id,
        at,
        href: `/messages?c=${event.conversation_id ?? ""}`,
        text: event.requires_ack ? "New message that needs your acknowledgement" : "New message",
      };
    case "message.acknowledged":
      return { id, at, href: "/messages", text: "Someone acknowledged your message" };
    case "task.assigned":
      return { id, at, href: "/tasks", text: "A task was assigned to you" };
    case "task.updated":
      return {
        id,
        at,
        href: "/tasks",
        text: `A task was updated${event.status ? ` (${event.status.replace("_", " ")})` : ""}`,
      };
    case "report.requested":
      return { id, at, href: "/reports", text: "The Director requested a report" };
    default:
      return null;
  }
}

/** Keep the newest notices first, without duplicates, capped. */
export function addNotice(list: Notice[], notice: Notice, cap = 20): Notice[] {
  return [notice, ...list.filter((n) => n.id !== notice.id)].slice(0, cap);
}

export function soundFor(event: RealtimeEvent): "message" | "notification" | null {
  if (event.type === "message.created") return "message";
  if (event.type === "task.assigned" || event.type === "report.requested") return "notification";
  return null;
}

/** Same-origin WebSocket URL for the event stream. */
export function socketUrl(location: { protocol: string; host: string }): string {
  return `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/api/v1/ws`;
}
