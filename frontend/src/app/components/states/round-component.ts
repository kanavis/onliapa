import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { IGameState } from 'src/app/game/interfaces';

@Component({
  templateUrl: './round.component.html',
  selector: 'app-round',
})
export class RoundComponent implements OnChanges {
  @Input() state: IGameState;
  timeLeft = 0;
  timerInterval?: number;

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.state.currentValue !== changes.state.previousValue) {
      this._runTimer();
    }
  }

  private _runTimer() {
    this.timeLeft = this.state.state_round.time_left;
    if (this.timerInterval !== undefined){
      window.clearInterval(this.timerInterval);
    }
    this.timerInterval = window.setInterval(this._timer.bind(this), 1000);
  }

  private _timer() {
    this.timeLeft--;
    if (this.timeLeft === 0) {
      window.clearInterval(this.timerInterval);
    }
  }

}
