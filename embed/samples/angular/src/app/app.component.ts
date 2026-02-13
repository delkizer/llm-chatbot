import { Component, ViewChild, ElementRef, AfterViewInit } from '@angular/core'

@Component({
  selector: 'app-root',
  template: `
    <div class="sample-page">
      <h1>Angular - spo-chatbot Sample</h1>

      <div class="controls">
        <label>Token:
          <input [(ngModel)]="token" (ngModelChange)="updateToken()" type="text" placeholder="JWT token" />
        </label>
        <label>Theme:
          <select [(ngModel)]="theme" (ngModelChange)="updateTheme()">
            <option value="default">Default</option>
            <option value="bwf">BWF</option>
            <option value="bxl">BXL</option>
          </select>
        </label>
        <label>Match ID:
          <input [(ngModel)]="matchId" (ngModelChange)="updateMatchId()" type="text" placeholder="match ID" />
        </label>
      </div>

      <div class="chatbot-container">
        <spo-chatbot
          #chatbot
          api-url="__CHATBOT_API_URL__"
          [attr.token]="token"
          [attr.theme]="theme"
          context-type="badminton"
          [attr.match-id]="matchId">
        </spo-chatbot>
      </div>
    </div>
  `,
  styles: [`
    :host {
      display: block;
    }
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }
    .sample-page {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 24px;
      min-height: 100vh;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #f5f5f5;
      color: #333;
    }
    h1 {
      font-size: 1.4rem;
      margin-bottom: 16px;
    }
    .controls {
      display: flex;
      gap: 16px;
      flex-wrap: wrap;
      align-items: center;
      margin-bottom: 20px;
      padding: 16px;
      background: #fff;
      border-radius: 8px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .controls label {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.9rem;
      font-weight: 500;
    }
    .controls input,
    .controls select {
      padding: 6px 10px;
      border: 1px solid #d1d5db;
      border-radius: 4px;
      font-size: 0.9rem;
    }
    .controls input {
      width: 180px;
    }
    .chatbot-container {
      width: 400px;
      height: 600px;
    }
    spo-chatbot {
      display: block;
      width: 100%;
      height: 100%;
    }
  `]
})
export class AppComponent implements AfterViewInit {
  @ViewChild('chatbot') chatbotRef!: ElementRef

  token = 'dev-test-token'
  theme = 'bwf'
  matchId = 'test-match-001'

  ngAfterViewInit() {
    console.log('chatbot element:', this.chatbotRef.nativeElement.tagName)
  }

  updateToken() {
    this.chatbotRef.nativeElement.setAttribute('token', this.token)
  }

  updateTheme() {
    this.chatbotRef.nativeElement.setAttribute('theme', this.theme)
  }

  updateMatchId() {
    this.chatbotRef.nativeElement.setAttribute('match-id', this.matchId)
  }
}
