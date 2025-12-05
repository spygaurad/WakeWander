const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export interface StreamEvent {
  type: string;
  step?: string;
  content?: string;
  conversation_id?: string;
  data?: any;
  interrupt_type?: 'question' | 'location_selection';
  question?: string;
  field?: string;
  options?: any[];
  missing_info?: string[];
  budget_allocation?: any;
}

export async function* streamChat(
  message: string,
  conversationId?: string
): AsyncGenerator<StreamEvent> {
  const response = await fetch(`${API_BASE_URL}/chat/stream`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({message, conversation_id: conversationId || null}),
  });

  if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();
  if (!reader) throw new Error('No reader available');

  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          yield JSON.parse(line.slice(6));
        } catch (e) {
          console.error('Failed to parse SSE:', e);
        }
      }
    }
  }
}

export async function* resumeChat(
  conversationId: string,
  value: any
): AsyncGenerator<StreamEvent> {
  const response = await fetch(`${API_BASE_URL}/chat/resume`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      conversation_id: conversationId,
      value: value,
    }),
  });

  if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();
  if (!reader) throw new Error('No reader available');

  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          yield JSON.parse(line.slice(6));
        } catch (e) {
          console.error('Failed to parse SSE:', e);
        }
      }
    }
  }
}

export async function createNewConversation(): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/conversation/new`, {method: 'POST'});
  if (!response.ok) throw new Error('Failed to create conversation');
  const data = await response.json();
  return data.conversation_id;
}
