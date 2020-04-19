import {Component, ElementRef, ViewChild} from '@angular/core';
import {WebSocketService} from '../services/ws/websocket.service';
import {IAuthRequest} from './interfaces';


@Component({
  template: `
    <div class="center">
      <div class="form">
        <div>
          <label>Имя пользователя:
            <input type="text" [(ngModel)]="username" autofocus #usernameEl>
          </label>
          <span class="red" *ngIf="usernameError">{{usernameError}}</span>
        </div>
        <button (click)="login()">АГА ХОЧУ ИГРАТЬ ДАВАЙ ИГРАТЬ УЖЕ ИГРАТЬ ИГРАТЬ!!!</button>
      </div>
    </div>
  `,
  selector: 'app-game-auth',
})
export class GameAuthComponent {
  username = '';
  usernameError = '';
  @ViewChild('usernameEl') usernameEl: ElementRef;

  constructor(private ws: WebSocketService) {
    const username = localStorage.getItem('gameLastUsername');
    if (username) {
      this.username = username;
    }
  }

  public login() {
    const username = this.username.trim();
    this.usernameError = '';
    if (!username) {
      this.usernameError = 'ПУСТОЙ ЛОГИН НИХЕРА';
      this.usernameEl.nativeElement.focus();
      return;
    } else if (username.toLowerCase() === 'admin') {
      this.usernameError = 'ЭТО ХЕРОВОЕ ИМЯ ВЫБЕРИ ДРУГОЕ (пожалуйста)';
      this.usernameEl.nativeElement.focus();
      return;
    }
    const message: IAuthRequest = {
      user_name: this.username,
    };
    this.ws.send('auth', message);
  }

}
