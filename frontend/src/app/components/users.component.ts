import { Component, Input, Output, EventEmitter } from '@angular/core';
import { IUser, IUserPair, IGameState } from '../game/interfaces';

@Component({
  templateUrl: './users.component.html',
  selector: 'app-users',
})
export class UsersComponent{
  @Input() state: IGameState;
  @Input() admin: boolean;
  @Input() unlocked: boolean;
  @Output() runPair = new EventEmitter<IUserPair>();

  userNameFrom: string;
  userIdFrom: number;
  userNameTo: string;
  userIdTo: number;

  public get sortedUsers(): Array<IUser> {
    return this.state.users.sort((a, b) => a.score - b.score);
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

}
