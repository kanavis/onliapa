import { Component, Input, Output, EventEmitter } from '@angular/core';
import { IUser, IAdminStartRound, IGameState } from '../game/interfaces';

@Component({
  templateUrl: './users.component.html',
  selector: 'app-users',
})
export class UsersComponent{
  @Input() state: IGameState;
  @Input() admin: boolean;
  @Input() user?: IUser;
  @Output() runPair = new EventEmitter<IAdminStartRound>();
  @Output() kickUser = new EventEmitter<number>();

  userNameFrom: string;
  userIdFrom: number;
  userNameTo: string;
  userIdTo: number;

  public get sortedUsers(): Array<IUser> {
    return this.state.users.sort((a, b) => b.score - a.score);
  }

  public setUserFrom(user: IUser) {
    this.userNameFrom = user.user_name;
    this.userIdFrom = user.user_id;
  }

  public resetUserId() {
    this.userIdFrom = undefined;
    this.userNameFrom = undefined;
    this.userIdTo = undefined;
    this.userNameTo = undefined;
  }

  public setUserTo(user: IUser) {
    if (this.userIdFrom === undefined) {
      throw new Error('Error 6661313');
    }
    this.userNameTo = user.user_name;
    this.userIdTo = user.user_id;
  }

  public emitRound() {
    if (this.userIdFrom === undefined) {
      throw new Error('Error 6661314');
    }
    if (this.userIdTo === undefined) {
      throw new Error('Error 6661315');
    }
    this.runPair.emit({
      user_id_from: this.userIdFrom,
      user_id_to: this.userIdTo,
    });
    this.resetUserId();
  }

  public emitKickUser(user: IUser) {
    if (!confirm(`Кикаем нахер ${user.user_name}?`)) {
      return;
    }
    this.kickUser.next(user.user_id);
  }

  get unlocked(): boolean {
    return this.state.state_name === 'standby' && this.state.game_info.hat_words_left > 0;
  }

  public showUser(user: IUser) {
    alert(`Это ${user.user_name}.
Он угадал ${user.guessed_words.length} слов. Молодец!
${user.guessed_words.join(', ')}`);
  }

}
