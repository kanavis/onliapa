// Interfaces

export interface IUrlConfig {
  schema: string;
  port: number;
  path: string;
  host?: string;
}

export interface IWsMessage<T> {
  tag: string;
  error?: string;
  message: T;
}
