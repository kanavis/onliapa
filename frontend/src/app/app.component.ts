import { Component, OnInit } from '@angular/core';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit {
  title = 'ТИПА ИГРА';

  ngOnInit(): void {
    setTimeout(() => {
      this.title = 'ПИПА ТИГРА';
    }, 60000);
  }
}
