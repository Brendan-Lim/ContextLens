import {copy} from '../../i18n/copy';import {ContactForm} from './ContactForm';import {NotificationCard} from './NotificationCard';import styles from './ContactForm.module.css';
export function SettingsWorkspace(){return <main><h1>{copy.settings.title}</h1><p className="lede">{copy.settings.description}</p><div className={styles.columns}><ContactForm/><NotificationCard/></div></main>;}
