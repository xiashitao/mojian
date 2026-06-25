import { elementClass } from "../../utils/ganzhi";

/** A 干支 string with each char tinted by its 五行. */
export function Ganzhi({ gz }: { gz: string }) {
  return (
    <>
      <span className={elementClass(gz[0])}>{gz[0]}</span>
      <span className={elementClass(gz[1])}>{gz[1]}</span>
    </>
  );
}
