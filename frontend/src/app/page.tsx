import { redirect } from 'next/navigation';

export default function Home() {
  // Redirect to chat as the main entry point
  redirect('/chat');
}
