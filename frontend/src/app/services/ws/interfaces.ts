import { Observable } from 'rxjs';

export interface WebSocketConfig {
  url: string;
  reconnectInterval?: number;
  reconnectAttempts?: number;
}

export interface IWsMessage<T> {
  tag: string;
  error: string;
  message: T;
}

export interface IWebsocketService {
  status: Observable<boolean>;
  on<T>(tag: string): Observable<T>;
  onError(): Observable<IWsMessage<null>>;
  send(tag: string, data: any): void;
}
