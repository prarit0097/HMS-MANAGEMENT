import { Component, type ReactNode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './styles.css';
class Boundary extends Component<{children:ReactNode},{failed:boolean}> {
  state={failed:false};
  static getDerivedStateFromError(){return {failed:true};}
  render(){return this.state.failed?<main className="boot"><h1>The workspace could not be displayed</h1><p>Refresh the page to load the latest records. Contact your administrator if this continues.</p><button className="button primary" onClick={()=>window.location.reload()}>Refresh workspace</button></main>:this.props.children;}
}
createRoot(document.getElementById('root')!).render(<Boundary><App/></Boundary>);
