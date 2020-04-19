import {Component, Input, OnInit} from '@angular/core';
import {IGameState, IHatAddWords, IUser, IUserId, IUserState} from './interfaces';
import {WebSocketService} from '../services/ws/websocket.service';


@Component({
  templateUrl: './game-play.component.html',
  selector: 'app-game-play',
})
export class GamePlayComponent implements OnInit {
  @Input('user') user: IUser;
  @Input('game_id') gameId: string;

  state: IGameState;
  userState: IUserState;
  stateUsersByUid: Map<number, IUser>;

  constructor(private ws: WebSocketService) {
    this.stateUsersByUid = new Map<number, IUser>();
  }

  ngOnInit() {
    // game state
    this.ws.on<IGameState>('game-state').subscribe(this._onGameState.bind(this));
    // user state
    this.ws.on<IUserState>('user-state').subscribe(this._onUserState.bind(this));
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
        if (newUser.user_id !== this.user.user_id && this.state) {
          this.state.users.push(newUser);
          this.stateUsersByUid.set(newUser.user_id, newUser);
        }
      }
    );
  }

  private _onGameState(state: IGameState) {
    console.log('Updated game state', state);
    this.state = state;
    const stateUsersByUid = new Map<number, IUser>();
    this.state.users.forEach(user => {
      stateUsersByUid[user.user_id] = user;
    });
  }

  private _onUserState(state: IUserState) {
    console.log('Updated user state', state);
    this.userState = state;
  }

  public sendHatWords(words: Array<string>) {
    const message: IHatAddWords = {
      words,
    };
    this.ws.send('hat-add-words', message);
  }


}
