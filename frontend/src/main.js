import { createApp } from "vue";
import { createPinia } from "pinia";
import router from "./router";
import { useGameStore } from "./store/game";
import App from "./App.vue";
import "./assets/base.css";

const app = createApp(App);
const pinia = createPinia();
app.use(pinia).use(router);

const store = useGameStore(pinia);
store.loadSession();
store.connectSocket();
store.joinSocketRoom();

app.mount("#app");
