import { ChatsCircle, Gear, MagnifyingGlass, SquaresFour, User, Users } from '@phosphor-icons/react';
export function BookCommunityNav({active}:{active:'feed'|'discover'|'me'|'messages'}){
 const items=[{id:'feed',title:'Все темы',icon:SquaresFour},{id:'discover',title:'Найти людей',icon:MagnifyingGlass},{id:'me',title:'Мой профиль',icon:User},{id:'messages',title:'Сообщения',icon:ChatsCircle},{id:'settings',title:'Настройки',icon:Gear}];
 return <nav className="book-community-nav" aria-label="Разделы сообщества"><p><Users size={23}/>Сообщество</p>{items.map(item=><a href={`#/${item.id}`} key={item.id} aria-current={active===item.id?'page':undefined}><item.icon size={22}/>{item.title}</a>)}</nav>;
}
