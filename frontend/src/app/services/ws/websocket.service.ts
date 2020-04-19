import { Injectable } from '@angular/core';
import { Observable, Subject, Subscription } from 'rxjs';
import { WebSocketSubject, webSocket } from 'rxjs/webSocket';
import { filter, map } from 'rxjs/operators';
import {IUrlConfig, IWsMessage} from './interfaces';


@Injectable()
export class WebSocketService {

  wsSubject: Subject<IWsMessage<any>>;
  ws: WebSocketSubject<IWsMessage<any>>;
  wsSub: Subscription;
  openSubject: Subject<Event>;
  closeSubject: Subject<CloseEvent>;
  connectError: Subject<Event>;

  constructor() {
    this.wsSubject = new Subject<IWsMessage<any>>();
    this.openSubject = new Subject<Event>();
    this.closeSubject = new Subject<CloseEvent>();
    this.connectError = new Subject<any>();
  }

  public connect(urlConfig: IUrlConfig, subpath?: string) {
    const host = urlConfig.host ? urlConfig.host : window.location.hostname;
    let url = `${urlConfig.schema}${host}:${urlConfig.port}${urlConfig.path}`;
    if (subpath) {
      console.log('Ws subpath', subpath, urlConfig);
      url = `${url}/${subpath}`;
    }
    console.log(`Connecting to ws ${url}`);
    this.ws = webSocket({
      url,
      openObserver: this.openSubject,
      closeObserver: this.closeSubject,
    });
    this.wsSub = this.ws.subscribe({
      next: (message) => this.wsSubject.next(message),
      error: (error: Event) => {
        console.error('Websocket', error);
        this.connectError.next(error);
      },
    });
    this.closeSubject.subscribe((e) => console.log('Websocket closed', e.code, e.reason));
    this.openSubject.subscribe(() => console.log('Websocket connected'));
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
