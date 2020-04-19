import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';


@Component({
  template: `
    <div *ngIf="hatWords" class="small-form">
      <div *ngFor="let w of hatWords; let i = index; trackBy: customTrackBy">
        <label>
          {{i + 1}}: <input type="text" [(ngModel)]="hatWords[i]">
        </label>
      </div>
      <div *ngIf="hatWordsError" class="red">{{hatWordsError}}</div>
      <button (click)="emitSendWords()">ГОТОВО!</button>
    </div>
  `,
  selector: 'app-hat-words',
})
export class HatWordsComponent implements OnInit {
  @Input() number: number;
  @Output() sendWords = new EventEmitter<Array<string>>();

  hatWords: Array<string>;
  hatWordsError = '';

  customTrackBy(index: number, obj: any): any {
    return index;
  }

  ngOnInit() {
    this.hatWords = new Array<string>(this.number).fill('');
  }

  emitSendWords() {
    this.hatWordsError = '';
    const words = new Array<string>();
    console.log(this.hatWords);
    for (let word of this.hatWords) {
      word = word.toLowerCase().trim();
      if (!word) {
        this.hatWordsError = 'НАДО ЕЩЁ СЛОВА!';
        return;
      }
      words.push(word);
    }
    console.log('Sending words', words);
    this.sendWords.emit(words);
  }
}
