import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';
import { FormsModule } from '@angular/forms';


import { AppComponent } from './app.component';
import { NewGameComponent } from './new-game/new-game.component';
import { AppRoutingModule } from './app-routing.module';
import { WebSocketService } from './services/ws/websocket.service';
import { GameComponent } from './game/game.component';
import { AdminComponent } from './admin/admin.component';
import { UsersComponent } from './components/users.component';
import { StateComponent } from './components/state.component';
import { HatFillComponent } from './components/states/hat-fill.component';
import { RoundComponent } from './components/states/round-component';
import { GameAuthComponent } from './game/game-auth.component';
import {GamePlayComponent} from './game/game-play.component';
import {HatWordsComponent} from './components/states/hat-words.component';
import {StandbyComponent} from './components/states/standby.component';

@NgModule({
  declarations: [
    AppComponent,
    NewGameComponent,
    GameComponent,
    AdminComponent,
    StateComponent,
    UsersComponent,
    HatFillComponent,
    RoundComponent,
    GameAuthComponent,
    GamePlayComponent,
    HatWordsComponent,
    StandbyComponent,
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    FormsModule,
  ],
  providers: [
    WebSocketService,
  ],
  bootstrap: [AppComponent]
})
export class AppModule { }
