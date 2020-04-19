import { Component, ViewChild, ElementRef, OnInit, OnDestroy } from '@angular/core';
import { WebSocketService } from '../services/ws/websocket.service';
import { environment } from 'src/environments/environment';
import { INewGameRequest } from './interfaces';
import { Router } from '@angular/router';
import { Subscription } from 'rxjs';

@Component({
  templateUrl: './new-game.component.html',
})
export class NewGameComponent implements OnInit, OnDestroy {
  gameName = '';
  globalError = '';
  roundLength = 60;
  hatWordsPerUser = 5;
  formError = '';

  private routeSub: Subscription;

  @ViewChild('name') nameElement: ElementRef;
  @ViewChild('length') lengthElement: ElementRef;
  @ViewChild('words') wordsElement: ElementRef;

  constructor(private ws: WebSocketService, private router: Router) {}

  ngOnInit(): void {
    this.ws.on<string>('new-game-id').subscribe({
      next: (id: string) => {
        location.href = `/admin/${id}`;
      }
    });
    this.ws.onError().subscribe({
      next: (error) => {
        console.error('Ws error', error);
        alert(`Error (${error.tag}): ${error.error}`);
      }
    });
    this.ws.connectError.subscribe(() => this.globalError = 'Ошибка соединения');
    this.ws.connect(environment.ws_create);
  }

  public ngOnDestroy() {
    this.routeSub.unsubscribe();
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
