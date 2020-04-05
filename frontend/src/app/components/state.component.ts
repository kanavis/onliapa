import { Component, Input } from '@angular/core';
import { IGameState } from '../game/interfaces';

@Component({
  templateUrl: './state.component.html',
  selector: 'app-state',
})
export class StateComponent{
  @Input() state: IGameState;

  public get readableStateName(): string {
    if (this.state.state_name === 'hat_fill') {
      return 'Наполнение шляпы';
    } else if (this.state.state_name === 'standby') {
      return 'Ожидание';
    } else if (this.state.state_name === 'round') {
      return 'Раунд';
    } else {
      return 'unknown';
    }
  }

  public get gameHref(): string {
    const parts = window.location.href.split('/');
    const base = parts[0] + '//' + parts[2];
    return base + '/game/' + this.state.game_info.game_id;
  }

  public toClipboard(val: string){
    const selBox = document.createElement('textarea');
    selBox.style.position = 'fixed';
    selBox.style.left = '0';
    selBox.style.top = '0';
    selBox.style.opacity = '0';
    selBox.value = val;
    document.body.appendChild(selBox);
    selBox.focus();
    selBox.select();
    document.execCommand('copy');
    document.body.removeChild(selBox);
  }

}
