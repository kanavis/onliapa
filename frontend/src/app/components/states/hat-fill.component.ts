import {Component, EventEmitter, Input, Output} from '@angular/core';
import {IGameState, IUser} from 'src/app/game/interfaces';

@Component({
  templateUrl: './hat-fill.component.html',
  selector: 'app-hat-fill',
})
export class HatFillComponent {
  @Input() state: IGameState;
  @Input() user?: IUser;
  @Input() admin: boolean;
  @Output() sendWords = new EventEmitter<Array<string>>();
  @Output() hatComplete = new EventEmitter<boolean>();

  userFilled(userId: number): boolean {
    return !!this.state.state_hat_fill.users.find(user => {return userId === user});
  }

  get currentUserFills(): boolean {
    if (!this.user) {
      return false;
    }
    return !this.userFilled(this.user.user_id);
  }

  emitSendWords(words: Array<string>) {
    this.sendWords.emit(words);
  }

  get userNumberValid(): boolean {
    return this.state.users.length >= 2;
  }

  get hatHasWords(): boolean {
    return this.state.state_hat_fill && this.state.state_hat_fill.users.length > 0;
  }

  get hatFilled(): boolean {
    return this.state.state_hat_fill && this.state.state_hat_fill.users.length >= this.state.users.length;
  }

  get startGameAvailable(): boolean {
    return this.userNumberValid && this.hatHasWords;
  }

  get startGameReady(): boolean {
    return this.startGameAvailable && this.hatFilled;
  }

  emitHatComplete() {
    this.hatComplete.emit(!this.startGameReady);
  }

}
