
export interface IUser {
  user_name: string;
  user_id: number;
  score: number;
}

export interface IStateHatFill {
  users: Array<IUser>;
}

export interface IStateRound {
  asking: IUser;
  answering: IUser;
  time_left: number;
}

export interface IGameInfo {
  game_id: string;
  game_name: string;
  round_length: number;
  hat_words_per_user: number;
}

export interface IGameState {
  game_info: IGameInfo;
  state_name: string;
  state_hat_fill?: IStateHatFill;
  state_round?: IStateRound;
  users: Array<IUser>;
  reason?: string;
  appendix: any;
}

export interface IUserPair {
  user_id_from: number;
  user_id_to: number;
}
