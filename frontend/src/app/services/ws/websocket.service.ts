import { Injectable, Inject } from '@angular/core';
import { SubscriptionLike, Observable, Observer, Subject, config, interval } from 'rxjs';
import { WebSocketSubject, WebSocketSubjectConfig } from 'rxjs/webSocket';
import { share, distinctUntilChanged, takeWhile, filter, map } from 'rxjs/operators';
import { IWsMessage, WebSocketConfig, IWebsocketService } from './interfaces';
import { environment } from 'src/environments/environment';


@Injectable()
export class WebSocketService implements IWebsocketService {
  private config: WebSocketSubjectConfig<IWsMessage<any>>;
  private websocketSub: SubscriptionLike;
  private statusSub: SubscriptionLike;

  private reconnection$: Observable<number>;
  private websocket$: WebSocketSubject<IWsMessage<any>>;

  private connection$: Observer<boolean>;
  private wsMessages$: Subject<IWsMessage<any>>;
  private reconnectInterval: number;
  private reconnectAttempts: number;

  private isConnected: boolean;

  public status: Observable<boolean>;


  constructor() {
    this.wsMessages$ = new Subject<IWsMessage<any>>();
    this.reconnectInterval = 5000;
    this.reconnectAttempts = 10;

    this.config = {
        url: '',
        closeObserver: {
            next: (event: CloseEvent) => {
                console.log('Websocket close');
                this.websocket$ = null;
                this.connection$.next(false);
            }
        },
        openObserver: {
            next: (event: Event) => {
                console.log('WebSocket connected!');
                this.connection$.next(true);
            }
        }
    };

    this.status = new Observable<boolean>((observer) => {
        this.connection$ = observer;
    }).pipe(share(), distinctUntilChanged());

    this.statusSub = this.status
        .subscribe((isConnected) => {
            this.isConnected = isConnected;

            if (!this.reconnection$ && typeof(isConnected) === 'boolean' && !isConnected) {
                this.reconnect();
            }
        });

    this.websocketSub = this.wsMessages$.subscribe({
        error: (error: ErrorEvent) => console.error('WebSocket error!', error)
    });

  }

  public connectToUrl(url: string) {
    this.config.url = url;
    console.log(`Opening websocket to ${url}`);
    this.connect();
  }

  private connect(): void {
    if (this.websocket$) {
      this.websocket$.complete();
    }
    this.websocket$ = new WebSocketSubject(this.config);
    this.websocket$.complete();
    console.log('Subscribing websocket');
    this.websocket$.subscribe(
      (message) => this.wsMessages$.next(message),
      (error: Event) => {
          if (!this.websocket$) {
              this.reconnect();
          }
    });
  }

  private reconnect(): void {
    this.reconnection$ = interval(this.reconnectInterval)
        .pipe(takeWhile((v, index) => index < this.reconnectAttempts && !this.websocket$));

    this.reconnection$.subscribe({
      next: () => this.connect(),
      complete: () => {
          this.reconnection$ = null;
          console.log('Reconnection complete');
          if (!this.websocket$) {
              this.wsMessages$.complete();
              this.connection$.complete();
          }
      }
    });
  }

  public on<T>(tag: string): Observable<T> {
    return this.wsMessages$.pipe(
        filter((message: IWsMessage<T>) => message.tag === tag),
        filter((message: IWsMessage<T>) => 'message' in message ),
        map((message: IWsMessage<T>) => message.message)
    );
  }

  public onError(): Observable<IWsMessage<null>> {
    return this.wsMessages$.pipe(
      filter((message: IWsMessage<null>) => 'error' in message),
    );
  }

  public send(tag: string, message: any = {}): void {
    if (tag && this.isConnected) {
        this.websocket$.next(JSON.stringify({ tag, message }) as any);
    } else {
        console.error('Send error!');
    }
  }

}
