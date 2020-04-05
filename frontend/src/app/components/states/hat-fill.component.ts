import { Component, Input } from '@angular/core';
import { IGameState } from 'src/app/game/interfaces';

@Component({
  templateUrl: './hat-fill.component.html',
  selector: 'app-hat-fill',
})
export class HatFillComponent {
  @Input() state: IGameState;
}
