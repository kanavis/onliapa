import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';
import { FormsModule } from '@angular/forms';


import { AppComponent } from './app.component';
import { NewGameComponent } from './new-game/new-game.component';
import { AppRoutingModule } from './app-routing.module';
import { WebSocketService } from './services/ws/websocket.service';

@NgModule({
  declarations: [
    AppComponent,
    NewGameComponent,
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
