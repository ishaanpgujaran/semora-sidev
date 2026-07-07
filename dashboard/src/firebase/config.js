/**
 * @file config.js
 * @description Configures the public Firebase client SDK settings for the frontend app.
 */

import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";
import { getFirestore } from "firebase/firestore";

// Public web client configuration options.
// This config is safe to include directly in the frontend source.
export const firebaseConfig = {
  apiKey: "AIzaSyC91JqBmOOA2BmyKzJUOPGRnr5_AasI9GU",
  authDomain: "semora-sidev.firebaseapp.com",
  projectId: "semora-sidev",
  storageBucket: "semora-sidev.firebasestorage.app",
  messagingSenderId: "1004142364430",
  appId: "1:1004142364430:web:0618d82a98d9d77f17b95f",
  measurementId: "G-Z5BD8GFBKD"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize and export Firebase services
export const auth = getAuth(app);
export const db = getFirestore(app);
