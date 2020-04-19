
export interface IUser {
  user_name: string;
  user_id: number;
  score: number;
  guessed_words: Array<string>;
}

export interface IUserId {
  user_id: number;
}

export interface IStateHatFill {
  users: Array<number>;
}

export interface IStateRound {
  asking: IUser;
  answering: IUser;
  time_left: number;
  guessed_words: Array<string>;
}

export interface IGameInfo {
  game_id: string;
  game_name: string;
  round_length: number;
  hat_words_per_user: number;
  round_num: number;
  hat_words_left: number;
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

export interface IAdminStartRound {
  user_id_from: number;
  user_id_to: number;
}

export interface IAuthUser {
  user_name: string;
  user_id: number;
}

export interface IAuthRequest {
  user_name: string;
}

export interface IUserStateAsking {
  time_left: number;
  word: string;
  other: IUser;
}

export interface IUserStateAnswering {
  time_left: number;
  other: IUser;
}

export interface IUserState {
  state_name: string;
  state_asking: IUserStateAsking;
  state_answering: IUserStateAnswering;
}

export interface IHatAddWords {
  words: Array<string>;
}

export interface IHatFillEnd {
  ignore_not_full: boolean;
}
