import { Component, OnInit } from '@angular/core';
import {environment} from '../../environments/environment';
import {ActivatedRoute} from '@angular/router';
import {WebSocketService} from '../services/ws/websocket.service';
import {IWsMessage} from '../services/ws/interfaces';
import {IAuthUser} from './interfaces';

@Component({
  templateUrl: './game.component.html'
})
export class GameComponent implements OnInit {
  gameId: string;
  globalError: string;
  user?: IAuthUser;
  init = false;

  constructor(private route: ActivatedRoute, private ws: WebSocketService) {}

  ngOnInit() {
    this.gameId = this.route.snapshot.paramMap.get('id');
    this.ws.connectError.subscribe((error) => this.globalError =  `АШИПКА СОЕДИНЕНИЯ`);
    this.ws.onError().subscribe(this._onError.bind(this));
    this.ws.connect(environment.ws_game, this.gameId);
    this.ws.openSubject.subscribe(() => this.init = true);
    this.ws.on<IAuthUser>('auth-ok').subscribe(
      (user) => {
        localStorage.setItem('gameLastUsername', user.user_name);
        this.user = user;
      },
    );
  }

  private _onError(error: IWsMessage<any>) {
    console.error('Ws error', error);
    const tag = error.tag;
    if (tag === 'wrong-game') {
      console.error('Wrong game');
      this.globalError = 'Нет такой игры (((( :\'(((';
      this.init = false;
    } else if (tag === 'kick') {
      this.globalError = 'Вас кикнули(((';
      this.init = false;
    } else {
      this.globalError = `Ошибка: ${tag}`;
      this.init = false;
    }
  }
}
