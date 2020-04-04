import { Component, ViewChild, ElementRef, OnInit } from '@angular/core';
import { WebSocketService } from '../services/ws/websocket.service';
import { environment } from 'src/environments/environment';
import { INewGameRequest } from './interfaces';

@Component({
  templateUrl: './new-game.component.html',
})
export class NewGameComponent implements OnInit {
  gameName = '';
  roundLength = 60;
  hatWordsPerUser = 5;
  formError = '';

  @ViewChild('name') nameElement: ElementRef;
  @ViewChild('length') lengthElement: ElementRef;
  @ViewChild('words') wordsElement: ElementRef;

  constructor(private ws: WebSocketService) {}

  ngOnInit(): void {
    console.log('Init create game controller');
    this.ws.connectToUrl(environment.ws_create);
  }

  submitForm() {
    if (this.gameName.length < 3 || this.gameName.length > 100) {
      this.formError = 'Длина хуимени должна быть от 3 до 100';
      this.nameElement.nativeElement.focus();
      return;
    }
    if (this.roundLength < 10 || this.roundLength > 10000) {
      this.formError = 'Длина хуйраунда должна быть от 10 до 10000';
      this.lengthElement.nativeElement.focus();
      return;
    }
    if (this.hatWordsPerUser < 1 || this.hatWordsPerUser > 100) {
      this.formError = 'Хуичество слов должно быть от 1 до 100';
      this.wordsElement.nativeElement.focus();
      return;
    }

    if (!confirm('Точна?')) {
      return;
    }
    const request: INewGameRequest = {
      game_name: this.gameName,
      round_length: this.roundLength,
      hat_words_per_user: this.hatWordsPerUser,
    };
    this.ws.send('new-game', request);
  }
}
