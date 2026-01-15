import { createRouter, createWebHistory } from "vue-router";
import HomeView from "../views/HomeView.vue";
import WaitingView from "../views/WaitingView.vue";
import GameView from "../views/GameView.vue";
import ResultView from "../views/ResultView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "home", component: HomeView },
    { path: "/room/:id/waiting", name: "waiting", component: WaitingView },
    { path: "/room/:id/game", name: "game", component: GameView },
    { path: "/room/:id/result", name: "result", component: ResultView }
  ]
});

export default router;
