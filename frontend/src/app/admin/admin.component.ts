import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { WebSocketService } from '../services/ws/websocket.service';
import { environment } from 'src/environments/environment';
import { IWsMessage } from '../services/ws/interfaces';
import {
  IGameState,
  IHatFillEnd,
  IUser,
  IUserId,
  IAdminStartRound
} from '../game/interfaces';


@Component({
  templateUrl: './admin.component.html'
})
export class AdminComponent implements OnInit {
  gameId: string;
  globalError: string;
  init = false;

  state: IGameState;
  stateUsersByUid: Map<number, IUser>;

  constructor(private route: ActivatedRoute, private ws: WebSocketService) {
    this.stateUsersByUid = new Map<number, IUser>();
  }

  ngOnInit() {
    this.gameId = this.route.snapshot.paramMap.get('id');
    this.ws.onError().subscribe(this._onError.bind(this));
    this.ws.connectError.subscribe((error) => this.globalError =  `АШИПКА СОЕДИНЕНИЯ`);
    this.ws.connect(environment.ws_admin, this.gameId);
    // Game state
    this.ws.on<IGameState>('game-state').subscribe(this._onGameState.bind(this));
    // Remove user
    this.ws.on<IUserId>('remove-user').subscribe(
      (rmUser) => {
        this.state.users = this.state.users.filter(user => user.user_id !== rmUser.user_id);
        this.stateUsersByUid.delete(rmUser.user_id);
      }
    );
    // Add user
    this.ws.on<IUser>('new-user').subscribe(
      (newUser) => {
        this.state.users.push(newUser);
        this.stateUsersByUid.set(newUser.user_id, newUser);
      }
    );
  }

  private _onError(error: IWsMessage<any>) {
    console.error('Ws error', error);
    const tag = error.tag;
    if (tag === 'wrong-game') {
      console.error('Wrong game');
      this.globalError = 'Нет такой игры (((( :\'(((';
      this.init = false;
    } else {
      alert(`Ошибка: ${tag}`);
    }
  }

  private _onGameState(state: IGameState) {
    console.log('Updated game state', state);
    /*
    state.users.push({
      user_name: 'anus tigra',
      user_id: 123,
      score: 123,
    });
    state.users.push({
      user_name: 'pupok pupok',
      user_id: 100,
      score: 11,
    });
    state.users.push({
      user_name: 'penis nigra',
      user_id: 124,
      score: 111,
    });
    state.state_name = 'round';
    state.state_hat_fill = undefined;
    state.state_round = {
      asking: {
        user_id: 123,
        user_name: 'anus tigra',
        score: 123,
      },
      answering: {
        user_name: 'penis_nigra',
        user_id: 124,
        score: 111,
      },
      time_left: 30,
    };
    */
    this.state = state;
    const stateUsersByUid = new Map<number, IUser>();
    this.state.users.forEach(user => {
      stateUsersByUid[user.user_id] = user;
    });
    this.init = true;
  }

  runPair(pair: IAdminStartRound) {
    console.log('Starting pair', pair);
    this.ws.send('start-round', pair);
  }

  kickUser(userId: number) {
    const message: IUserId = {
      user_id: userId,
    };
    console.log('Kicking user', userId);
    this.ws.send('kick-user', message);
  }

  hatComplete(ignoreNotFull) {
    console.log('Completing hat.', 'Ignore:', ignoreNotFull);
    const message: IHatFillEnd = {
      ignore_not_full: ignoreNotFull,
    };
    this.ws.send('hat-complete', message);
  }

}
