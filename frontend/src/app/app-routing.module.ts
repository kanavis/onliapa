import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { NewGameComponent } from './new-game/new-game.component';

const routes: Routes = [
  { path: '', redirectTo: '/new_game', pathMatch: 'full' },
  { path: 'new_game', component: NewGameComponent }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
