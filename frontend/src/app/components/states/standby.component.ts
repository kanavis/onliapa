import {Component, Input} from '@angular/core';
import {IGameState} from 'src/app/game/interfaces';

@Component({
  template: `
    <b *ngIf="state.game_info.hat_words_left > 0">Тупим (ждём начала раунда)</b>
    <div class="red" *ngIf="state.game_info.hat_words_left <= 0">
      Слова кончились. Всё. Пиздец.
    </div>
  `,
  selector: 'app-standby',
})
export class StandbyComponent {
  @Input() state: IGameState;
}
