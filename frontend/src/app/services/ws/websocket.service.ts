import { Injectable, Inject } from '@angular/core';
import { SubscriptionLike, Observable, Observer, Subject, config, interval, Subscription } from 'rxjs';
import { WebSocketSubject, webSocket } from 'rxjs/webSocket';
import { share, distinctUntilChanged, takeWhile, filter, map } from 'rxjs/operators';
import { IWsMessage, WebSocketConfig, IWebsocketService } from './interfaces';
import { environment } from 'src/environments/environment';


@Injectable()
export class WebSocketService {

  wsSubject: Subject<IWsMessage<any>>;
  ws: WebSocketSubject<IWsMessage<any>>;
  wsSub: Subscription;

  constructor() {
    this.wsSubject = new Subject<IWsMessage<any>>();
  }

  public connect(url: string) {
    console.log(`Connecting to ws ${url}`);
    this.ws = webSocket(url);
    this.wsSub = this.ws.subscribe({
      next: (message) => this.wsSubject.next(message),
      error: (error) => this._onError(error),
      complete: () => console.log(`websocket at ${url} complete ${this.ws.thrownError}`),
    });
  }

  public disconnect() {
    console.log('Websocket disconnected');
    this.wsSub.unsubscribe();
    this.ws.complete();
    this.ws = undefined;
  }

  private _onError(error: string) {
    console.error('Websocket', error);
  }

  public send(tag: string, message: any) {
    this.ws.next({message, tag});
  }

  public on<T>(tag: string): Observable<T> {
    return this.wsSubject.pipe(
      filter((message: IWsMessage<T>) => message.tag === tag),
      filter((message: IWsMessage<T>) => 'message' in message ),
      map((message: IWsMessage<T>) => message.message),
    );
  }

  public onError(): Observable<IWsMessage<null>> {
    return this.wsSubject.pipe(
      filter((message: IWsMessage<null>) => 'error' in message),
    );
  }

}
